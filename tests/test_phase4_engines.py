"""Focused deterministic tests for Phase 4 business components."""

import unittest

from app.comparison.comparison_engine import ComparisonEngine
from app.config.settings import Settings
from app.extractor.resume_evaluator import CandidateEvaluation
from app.formatter.report_formatter import ReportFormatter
from app.models.document import ExtractedJobDescription, ExtractedResume, Project
from app.ranking.ranking_engine import RankingEngine
from app.recommendation.recommendation_engine import RecommendationEngine
from app.scoring.scoring_engine import ScoringEngine


class Phase4EngineTests(unittest.TestCase):
    """Verify the deterministic rules without any Telegram or LLM requests."""

    def setUp(self) -> None:
        self.settings = Settings(telegram_bot_token="test-token", gemini_api_key="test-key")
        self.job_description = ExtractedJobDescription(
            job_title="Backend Engineer",
            required_skills=["Python", "SQL"],
            preferred_skills=["Docker"],
            certifications=["AWS"],
            experience="2 years",
            education=["BSc"],
            tech_stack=["FastAPI"],
        )
        self.resume = ExtractedResume(
            candidate_name="Ada",
            skills=["Python"],
            tools=["FastAPI"],
            projects=[Project(name="API", technologies=["Python", "FastAPI"])],
        )

    def test_comparison_is_repeatable(self) -> None:
        engine = ComparisonEngine()
        first = engine.compare(self.resume, self.job_description)
        second = engine.compare(self.resume, self.job_description)
        self.assertEqual(first, second)
        self.assertEqual(first.matched_skills, ["Python", "FastAPI"])
        self.assertEqual(first.missing_skills, ["SQL"])

    def test_score_is_repeatable_and_weights_are_configurable(self) -> None:
        comparison = ComparisonEngine().compare(self.resume, self.job_description)
        default_engine = ScoringEngine(self.settings)
        self.assertEqual(default_engine.score(comparison, self.resume), default_engine.score(comparison, self.resume))
        weighted_settings = Settings(
            telegram_bot_token="test-token",
            gemini_api_key="test-key",
            score_weight_technical_skills=80,
            score_weight_projects=20,
            score_weight_experience=0,
            score_weight_education=0,
            score_weight_certifications=0,
        )
        self.assertNotEqual(
            default_engine.score(comparison, self.resume).overall_score,
            ScoringEngine(weighted_settings).score(comparison, self.resume).overall_score,
        )

    def test_ranking_preserves_upload_order_for_ties(self) -> None:
        comparison = ComparisonEngine().compare(self.resume, self.job_description)
        score = ScoringEngine(self.settings).score(comparison, self.resume)
        rankings = RankingEngine().rank([score, score], [comparison, comparison])
        self.assertEqual([candidate.candidate_index for candidate in rankings], [0, 1])

    def test_formatter_includes_recruiter_summary_fields(self) -> None:
        comparison = ComparisonEngine().compare(self.resume, self.job_description)
        score = ScoringEngine(self.settings).score(comparison, self.resume)
        ranking = RankingEngine().rank([score], [comparison])
        report = ReportFormatter().detailed_candidate_report(
            score,
            comparison,
            CandidateEvaluation(strengths=["Relevant Python experience"]),
            RecommendationEngine().recommend(comparison.missing_skills),
        )
        self.assertIn("Overall Score", report)
        self.assertIn("Missing Technical Skills", report)
        self.assertIn("Recommended Courses", report)


if __name__ == "__main__":
    unittest.main()
