"""Unit tests for Phase 7 improvements: Session management, skill filtering, recommendations, and retry fallback."""

import unittest
from unittest.mock import MagicMock, patch

from app.config.settings import Settings
from app.comparison.comparison_models import ResumeComparisonResult
from app.extractor.resume_evaluator import CandidateEvaluation
from app.formatter.report_formatter import ReportFormatter, is_valid_skill, is_soft_skill
from app.llm.client import LLMClient, LLMGenerationError
from app.models.document import ExtractedJobDescription, ExtractedResume, Project
from app.models.upload import UploadSession, UploadMetadata, UploadType, ConversationState
from app.recommendation.recommendation_engine import RecommendationEngine
from app.scoring.score_models import CandidateScore, SectionScores
from app.services.conversation_manager import ConversationStateManager


class ImprovementTests(unittest.TestCase):
    """Test session resetting, report formatting, skill filtering, and recommendation catalog."""

    def setUp(self) -> None:
        self.settings = Settings(
            telegram_bot_token="test-token",
            gemini_api_key="test-key",
            gemini_model="gemini-3.6-flash",
            gemini_model_fallbacks="gemini-2.5-flash,gemini-2.0-flash",
        )

    def test_session_reset_for_next_batch_keeps_jd(self) -> None:
        """Verify reset_for_next_batch clears resumes and results but preserves JD."""
        session = UploadSession(
            user_id=123,
            state=ConversationState.READY_TO_PROCESS,
            job_description=UploadMetadata(
                original_filename="jd.pdf",
                stored_filename="jd_123.pdf",
                mime_type="application/pdf",
                size=1000,
                file_path="/tmp/jd.pdf",
                upload_type=UploadType.JOB_DESCRIPTION,
                telegram_file_id="id1",
            ),
            resumes=[
                UploadMetadata(
                    original_filename="resume.pdf",
                    stored_filename="resume_123.pdf",
                    mime_type="application/pdf",
                    size=500,
                    file_path="/tmp/resume.pdf",
                    upload_type=UploadType.RESUME,
                    telegram_file_id="id2",
                )
            ],
            extracted_resumes=[ExtractedResume(candidate_name="John Doe")],
        )

        session.reset_for_next_batch()

        self.assertIsNotNone(session.job_description)
        self.assertEqual(session.job_description.original_filename, "jd.pdf")
        self.assertEqual(len(session.resumes), 0)
        self.assertEqual(len(session.extracted_resumes), 0)
        self.assertEqual(session.state, ConversationState.WAITING_FOR_RESUMES)

    def test_conversation_manager_reset_resumes_keep_jd(self) -> None:
        """Verify ConversationStateManager.reset_resumes_keep_jd clears resume list and files."""
        mock_upload_service = MagicMock()
        manager = ConversationStateManager(mock_upload_service)
        session = manager.start_session(123)
        manager.record_job_description(
            123,
            UploadMetadata(
                original_filename="jd.pdf",
                stored_filename="jd_123.pdf",
                mime_type="application/pdf",
                size=1000,
                file_path="/tmp/jd.pdf",
                upload_type=UploadType.JOB_DESCRIPTION,
                telegram_file_id="id1",
            ),
        )
        manager.record_resume(
            123,
            UploadMetadata(
                original_filename="res.pdf",
                stored_filename="res_123.pdf",
                mime_type="application/pdf",
                size=500,
                file_path="/tmp/res.pdf",
                upload_type=UploadType.RESUME,
                telegram_file_id="id2",
            ),
        )

        manager.reset_resumes_keep_jd(123)

        updated_session = manager.get_session(123)
        self.assertIsNotNone(updated_session.job_description)
        self.assertEqual(len(updated_session.resumes), 0)
        self.assertEqual(updated_session.state, ConversationState.WAITING_FOR_RESUMES)

    def test_skill_helpers_and_report_formatter(self) -> None:
        """Verify invalid sentence skills are rejected and soft/technical skills are separated."""
        self.assertTrue(is_valid_skill("Python"))
        self.assertTrue(is_valid_skill("Machine Learning"))
        self.assertFalse(is_valid_skill("Candidate has extensive experience working with team members on agile projects."))
        self.assertFalse(is_valid_skill("Managed a team of 10 engineers in high-pressure environment."))

        self.assertTrue(is_soft_skill("Leadership"))
        self.assertTrue(is_soft_skill("Communication"))
        self.assertFalse(is_soft_skill("Kubernetes"))
        self.assertFalse(is_soft_skill("Python"))

        formatter = ReportFormatter()
        score = CandidateScore(
            candidate_name="Alice",
            overall_score=85.0,
            section_scores=SectionScores(
                technical_skills=35, projects=20, experience=15, education=10, certifications=5
            ),
            confidence_score=90.0,
        )
        comparison = ResumeComparisonResult(
            candidate_name="Alice",
            matched_skills=["Python", "Leadership"],
            missing_skills=["Docker", "Communication", "Experienced in microservices architecture for enterprise scale."],
            additional_skills=["FastAPI"],
            skill_coverage_percentage=50.0,
            project_coverage_percentage=100.0,
            experience_match=True,
            education_match=True,
        )
        report = formatter.detailed_candidate_report(
            score=score,
            comparison=comparison,
            evaluation=CandidateEvaluation(strengths=["Strong Python"]),
            recommendations=[],
        )

        self.assertIn("Matched Technical Skills: Python", report)
        self.assertIn("Missing Technical Skills: Docker", report)
        self.assertIn("Missing Soft Skills: Communication", report)
        self.assertIn("Additional Skills: FastAPI", report)
        self.assertNotIn("microservices architecture for enterprise scale", report)

    def test_expanded_recommendation_catalog(self) -> None:
        """Verify courses exist for all 12 requested skills."""
        engine = RecommendationEngine()
        skills = ["sql", "excel", "python", "java", "docker", "aws", "react", "mongodb", "r", "sas", "vba", "kubernetes"]
        recs = engine.recommend(skills, limit=12)
        self.assertEqual(len(recs), 12)
        mapped_skills = [r.reason.split(":")[-1].strip().rstrip(".") for r in recs]
        self.assertEqual(mapped_skills, skills)

    def test_llm_client_fallback_chain(self) -> None:
        """Verify LLMClient retries transient errors and switches models in preferred fallback order."""
        llm = LLMClient(self.settings)

        attempt_log = []

        def mock_request(prompt, model):
            attempt_log.append(model)
            if model == "gemini-3.6-flash":
                raise RuntimeError("503 Service Unavailable")
            elif model == "gemini-2.5-flash":
                raise RuntimeError("429 Too Many Requests")
            elif model == "gemini-2.0-flash":
                return {"status": "ok"}
            raise RuntimeError("Unknown model")

        with patch.object(llm, "_request_gemini", side_effect=mock_request), patch("time.sleep"):
            result = llm.generate_json("test prompt")
            self.assertEqual(result, {"status": "ok"})
            self.assertIn("gemini-3.6-flash", attempt_log)
            self.assertIn("gemini-2.5-flash", attempt_log)
            self.assertIn("gemini-2.0-flash", attempt_log)

    def test_llm_client_honors_retry_info_delay(self) -> None:
        """RetryInfo retryDelay takes precedence over exponential backoff."""
        llm = LLMClient(self.settings)
        quota_error = RuntimeError("429 RESOURCE_EXHAUSTED")
        quota_error.code = 429
        quota_error.details = {
            "error": {
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.RetryInfo",
                        "retryDelay": "24.5s",
                    }
                ]
            }
        }

        with patch.object(llm, "_request_gemini", side_effect=[quota_error, {"status": "ok"}]), patch(
            "time.sleep"
        ) as sleep:
            self.assertEqual(llm._generate_with_gemini("test prompt", "gemini-3.6-flash"), {"status": "ok"})

        sleep.assert_called_once_with(24.5)

    def test_llm_client_skips_404_models_and_uses_later_fallback(self) -> None:
        """Unavailable models do not terminate the configured fallback chain."""
        llm = LLMClient(self.settings)
        attempt_log = []

        def mock_request(prompt, model):
            attempt_log.append(model)
            if model in {"gemini-3.6-flash", "gemini-2.5-flash"}:
                error = RuntimeError("404 NOT_FOUND")
                error.code = 404
                raise error
            return {"status": "ok"}

        with patch.object(llm, "_request_gemini", side_effect=mock_request):
            self.assertEqual(llm.generate_json("test prompt"), {"status": "ok"})

        self.assertEqual(attempt_log, ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.0-flash"])

    def test_llm_client_returns_empty_payload_only_after_all_models_fail(self) -> None:
        """Qualitative evaluation degrades gracefully after the entire chain is exhausted."""
        llm = LLMClient(self.settings.model_copy(update={"openrouter_api_key": ""}))
        unavailable = RuntimeError("404 NOT_FOUND")
        unavailable.code = 404

        with patch.object(llm, "_request_gemini", side_effect=[unavailable, unavailable, unavailable]):
            self.assertEqual(llm.generate_json("test prompt"), {})


if __name__ == "__main__":
    unittest.main()
