"""Small, lossless shape corrections for common LLM JSON variations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class ExtractionResponseNormalizer:
    """Normalize harmless JSON shape differences before strict model validation."""

    _RESUME_STRING_LIST_FIELDS = (
        "skills",
        "certifications",
        "achievements",
        "languages",
        "tools",
        "frameworks",
        "databases",
        "cloud",
        "soft_skills",
    )
    _JD_STRING_LIST_FIELDS = (
        "required_skills",
        "preferred_skills",
        "responsibilities",
        "education",
        "certifications",
        "tech_stack",
    )
    _JD_OPTIONAL_STRING_FIELDS = ("job_title", "experience", "location")
    _RESUME_KEY_ALIASES = {
        "candidateName": "candidate_name",
        "softSkills": "soft_skills",
    }
    _JD_KEY_ALIASES = {
        "jobTitle": "job_title",
        "requiredSkills": "required_skills",
        "preferredSkills": "preferred_skills",
        "techStack": "tech_stack",
        "technical_skills": "required_skills",
        "technicalSkills": "required_skills",
        "soft_skills": "preferred_skills",
        "softSkills": "preferred_skills",
    }

    @classmethod
    def normalize_resume(cls, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Shape a resume response without coercing its values or relaxing validation."""
        normalized = cls._rename_known_keys(payload, cls._RESUME_KEY_ALIASES)
        for field in cls._RESUME_STRING_LIST_FIELDS:
            if field in normalized:
                normalized[field] = cls._string_as_list(normalized[field])
        for field in ("projects", "experience", "education"):
            if field in normalized:
                normalized[field] = cls._object_as_list(normalized[field])

        if isinstance(normalized.get("experience"), list):
            normalized["experience"] = [
                cls._normalize_experience(item) for item in normalized["experience"]
            ]
        if isinstance(normalized.get("projects"), list):
            normalized["projects"] = [
                cls._normalize_project(item) for item in normalized["projects"]
            ]
        return normalized

    @classmethod
    def normalize_job_description(cls, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Coerce harmless JD output variations into the strict schema's shapes.

        The comparison engine expects ``experience`` to be a single optional
        string and all requirements to be string lists, so those types remain
        unchanged after normalization.
        """
        normalized = cls._rename_jd_keys(payload)
        for field in cls._JD_STRING_LIST_FIELDS:
            if field in normalized:
                normalized[field] = cls.normalize_string_list(normalized[field])
        for field in cls._JD_OPTIONAL_STRING_FIELDS:
            if field in normalized:
                normalized[field] = cls.normalize_optional(normalized[field])
        return normalized

    @classmethod
    def normalize_string(cls, value: Any) -> str:
        """Return a readable string for scalar, list, or object LLM values."""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, Mapping):
            parts = [
                f"{str(key).replace('_', ' ')}: {cls.normalize_string(item)}"
                for key, item in value.items()
                if cls.normalize_optional(item) is not None
            ]
            return "; ".join(part for part in parts if part)
        if isinstance(value, (list, tuple, set)):
            return "; ".join(cls.normalize_string_list(value))
        return str(value).strip()

    @classmethod
    def normalize_string_list(cls, value: Any) -> list[str]:
        """Return a de-duplicated list of readable strings from LLM output."""
        if value is None:
            return []
        values = value if isinstance(value, (list, tuple, set)) else [value]
        normalized: list[str] = []
        seen: set[str] = set()
        for item in values:
            if item is None:
                continue
            text = cls.normalize_string(item)
            key = text.casefold()
            if text and key not in seen:
                normalized.append(text)
                seen.add(key)
        return normalized

    @classmethod
    def normalize_optional(cls, value: Any) -> str | None:
        """Return ``None`` for empty values, otherwise a readable string."""
        if value is None:
            return None
        text = cls.normalize_string(value)
        return text or None

    @classmethod
    def _rename_jd_keys(cls, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Move JD aliases into schema fields, merging aliased requirement lists."""
        normalized = dict(payload)
        for source, target in cls._JD_KEY_ALIASES.items():
            if source not in normalized:
                continue
            source_value = normalized.pop(source)
            if target in cls._JD_STRING_LIST_FIELDS:
                normalized[target] = cls.normalize_string_list(
                    [*cls.normalize_string_list(normalized.get(target)), *cls.normalize_string_list(source_value)]
                )
            elif target not in normalized:
                normalized[target] = source_value
        return normalized

    @staticmethod
    def _rename_known_keys(payload: Mapping[str, Any], aliases: Mapping[str, str]) -> dict[str, Any]:
        normalized = dict(payload)
        for source, target in aliases.items():
            if source in normalized and target not in normalized:
                normalized[target] = normalized.pop(source)
        return normalized

    @staticmethod
    def _string_as_list(value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return value

    @staticmethod
    def _object_as_list(value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, Mapping):
            return [dict(value)]
        return value

    @classmethod
    def _normalize_experience(cls, value: Any) -> Any:
        if not isinstance(value, Mapping):
            return value
        normalized = dict(value)
        if "description" in normalized:
            normalized["description"] = cls._string_as_list(normalized["description"])
        return normalized

    @classmethod
    def _normalize_project(cls, value: Any) -> Any:
        if not isinstance(value, Mapping):
            return value
        normalized = dict(value)
        if "technologies" in normalized:
            normalized["technologies"] = cls._string_as_list(normalized["technologies"])
        return normalized
