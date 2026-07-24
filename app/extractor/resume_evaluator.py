"""Qualitative AI evaluation that never produces numerical scores."""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.comparison.comparison_models import ResumeComparisonResult
from app.llm.client import LLMClient, LLMGenerationError
from app.models.document import ExtractedJobDescription, ExtractedResume


class CandidateEvaluation(BaseModel):
    """Strict qualitative insights generated after deterministic scoring."""

    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    missing_skills_explanation: list[str] = Field(default_factory=list)
    interview_readiness: str | None = None
    hiring_recommendation: str | None = None
    resume_feedback: list[str] = Field(default_factory=list)


class ResumeEvaluationError(RuntimeError):
    """Raised when qualitative evaluation cannot be validated."""


class ResumeEvaluator:
    """Ask the LLM for qualitative reasoning only, never a score or rank."""

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    def evaluate(
        self,
        resume: ExtractedResume,
        job_description: ExtractedJobDescription,
        comparison: ResumeComparisonResult,
    ) -> CandidateEvaluation:
        """Generate and strictly validate non-numerical recruiter insights."""
        try:
            payload = self._llm_client.generate_json(
                self._build_prompt(resume, job_description, comparison)
            )
            return CandidateEvaluation.model_validate(self._normalize_lists(payload))
        except (LLMGenerationError, ValidationError, ValueError) as error:
            raise ResumeEvaluationError("Could not generate qualitative candidate evaluation.") from error

    async def evaluate_async(
        self,
        resume: ExtractedResume,
        job_description: ExtractedJobDescription,
        comparison: ResumeComparisonResult,
    ) -> CandidateEvaluation:
        """Evaluate through the client's concurrency-limited Gemini entry point."""
        try:
            payload = await self._llm_client.generate_json_async(
                self._build_prompt(resume, job_description, comparison)
            )
            return CandidateEvaluation.model_validate(self._normalize_lists(payload))
        except (LLMGenerationError, ValidationError, ValueError) as error:
            raise ResumeEvaluationError("Could not generate qualitative candidate evaluation.") from error

    @staticmethod
    def _build_prompt(
        resume: ExtractedResume,
        job_description: ExtractedJobDescription,
        comparison: ResumeComparisonResult,
    ) -> str:
        template = (Path(__file__).resolve().parents[1] / "prompts" / "resume_evaluation.txt").read_text(encoding="utf-8")
        return (
            template.replace("{{resume}}", json.dumps(resume.model_dump(), ensure_ascii=False))
            .replace("{{job_description}}", json.dumps(job_description.model_dump(), ensure_ascii=False))
            .replace("{{comparison}}", json.dumps(comparison.model_dump(), ensure_ascii=False))
        )

    @staticmethod
    def _normalize_lists(payload: dict[str, object]) -> dict[str, object]:
        normalized = dict(payload)
        for field in ("strengths", "weaknesses", "missing_skills_explanation", "resume_feedback"):
            if isinstance(normalized.get(field), str):
                normalized[field] = [normalized[field]]
            elif normalized.get(field) is None:
                normalized[field] = []
        return normalized
