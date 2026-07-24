"""Deterministic, configurable scoring for comparison results."""

from app.comparison.comparison_models import ResumeComparisonResult
from app.config.settings import Settings
from app.models.document import ExtractedResume
from app.scoring.score_models import CandidateScore, SectionScores


class ScoringEngine:
    """Calculate scores exclusively in Python from deterministic comparison facts."""

    def __init__(self, app_settings: Settings) -> None:
        self._weights = {
            "technical_skills": app_settings.score_weight_technical_skills,
            "projects": app_settings.score_weight_projects,
            "experience": app_settings.score_weight_experience,
            "education": app_settings.score_weight_education,
            "certifications": app_settings.score_weight_certifications,
        }

    def score(self, comparison: ResumeComparisonResult, resume: ExtractedResume) -> CandidateScore:
        """Calculate a repeatable 0–100 score without invoking an LLM."""
        technical = self._weights["technical_skills"] * comparison.skill_coverage_percentage / 100
        projects = self._weights["projects"] * comparison.project_coverage_percentage / 100
        experience = self._weights["experience"] if comparison.experience_match else 0.0
        education = self._weights["education"] if comparison.education_match else 0.0
        certification_targets = len(comparison.matched_certifications) + len(comparison.missing_certifications)
        certification_coverage = (
            100.0
            if certification_targets == 0
            else (len(comparison.matched_certifications) / certification_targets) * 100
        )
        certifications = self._weights["certifications"] * certification_coverage / 100
        sections = SectionScores(
            technical_skills=round(technical, 2),
            projects=round(projects, 2),
            experience=round(experience, 2),
            education=round(education, 2),
            certifications=round(certifications, 2),
        )
        overall = round(sum(sections.model_dump().values()), 2)
        confidence = self._confidence(resume)
        return CandidateScore(
            candidate_name=comparison.candidate_name,
            overall_score=overall,
            section_scores=sections,
            confidence_score=confidence,
            score_explanation=[
                f"Required skill coverage: {comparison.skill_coverage_percentage:.0f}%.",
                f"Project technology coverage: {comparison.project_coverage_percentage:.0f}%.",
                f"Experience requirement: {'met' if comparison.experience_match else 'not met'}.",
                f"Education requirement: {'met' if comparison.education_match else 'not met'}.",
            ],
        )

    @staticmethod
    def _confidence(resume: ExtractedResume) -> float:
        available = sum(
            bool(value)
            for value in (resume.candidate_name, resume.email, resume.phone, resume.location)
        ) + sum(bool(value) for value in (resume.skills, resume.experience, resume.education, resume.projects))
        return round((available / 8) * 100, 2)
