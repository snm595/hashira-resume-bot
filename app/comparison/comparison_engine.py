"""Deterministic comparison of extracted candidate facts against a job description."""

import re

from app.comparison.comparison_models import ResumeComparisonResult
from app.models.document import ExtractedJobDescription, ExtractedResume


class ComparisonEngine:
    """Compare normalized field values without AI inference or scoring."""

    def compare(
        self,
        resume: ExtractedResume,
        job_description: ExtractedJobDescription,
    ) -> ResumeComparisonResult:
        """Return repeatable matching facts for a single candidate."""
        candidate_skills = self._unique(
            [
                *resume.skills,
                *resume.tools,
                *resume.frameworks,
                *resume.databases,
                *resume.cloud,
            ]
        )
        required = self._unique([*job_description.required_skills, *job_description.tech_stack])
        preferred = self._unique(job_description.preferred_skills)
        matched, missing, partial = self._compare_terms(required, candidate_skills)
        matched_preferred, missing_preferred, _ = self._compare_terms(preferred, candidate_skills)
        matched_certifications, missing_certifications, _ = self._compare_terms(
            self._unique(job_description.certifications), self._unique(resume.certifications)
        )
        known_job_terms = {self._key(item) for item in [*required, *preferred]}
        additional = [item for item in candidate_skills if self._key(item) not in known_job_terms]
        project_terms = self._unique(
            technology for project in resume.projects for technology in project.technologies
        )
        project_targets = self._unique([*required, *preferred])
        project_matched, _, _ = self._compare_terms(project_targets, project_terms)
        return ResumeComparisonResult(
            candidate_name=resume.candidate_name or "Unnamed candidate",
            matched_skills=matched,
            missing_skills=missing,
            additional_skills=additional,
            partially_matched_skills=partial,
            matched_preferred_skills=matched_preferred,
            missing_preferred_skills=missing_preferred,
            matched_certifications=matched_certifications,
            missing_certifications=missing_certifications,
            skill_coverage_percentage=self._percentage(len(matched), len(required)),
            project_coverage_percentage=self._percentage(len(project_matched), len(project_targets)),
            experience_match=bool(resume.experience) if job_description.experience else True,
            education_match=bool(resume.education) if job_description.education else True,
        )

    def _compare_terms(self, targets: list[str], candidates: list[str]) -> tuple[list[str], list[str], list[str]]:
        matched: list[str] = []
        missing: list[str] = []
        partial: list[str] = []
        candidate_keys = {self._key(candidate) for candidate in candidates}
        for target in targets:
            target_key = self._key(target)
            if target_key in candidate_keys:
                matched.append(target)
            elif any(self._is_partial_match(target_key, candidate_key) for candidate_key in candidate_keys):
                partial.append(target)
            else:
                missing.append(target)
        return matched, missing, partial

    @staticmethod
    def _unique(values: list[str] | object) -> list[str]:
        unique: list[str] = []
        seen: set[str] = set()
        for value in values:  # type: ignore[union-attr]
            if not value or not isinstance(value, str):
                continue
            key = ComparisonEngine._key(value)
            if key and key not in seen:
                seen.add(key)
                unique.append(value.strip())
        return unique

    @staticmethod
    def _key(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()

    @staticmethod
    def _is_partial_match(target: str, candidate: str) -> bool:
        target_terms = set(target.split())
        candidate_terms = set(candidate.split())
        return bool(target_terms and candidate_terms and target_terms & candidate_terms)

    @staticmethod
    def _percentage(matched: int, total: int) -> float:
        return 100.0 if total == 0 else round((matched / total) * 100, 2)
