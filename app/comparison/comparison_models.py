"""Deterministic resume-to-job-description comparison results."""

from pydantic import BaseModel, ConfigDict, Field


class ResumeComparisonResult(BaseModel):
    """Facts discovered by comparing one extracted resume against one extracted JD."""

    model_config = ConfigDict(extra="forbid", strict=True)

    candidate_name: str
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    additional_skills: list[str] = Field(default_factory=list)
    partially_matched_skills: list[str] = Field(default_factory=list)
    matched_preferred_skills: list[str] = Field(default_factory=list)
    missing_preferred_skills: list[str] = Field(default_factory=list)
    matched_certifications: list[str] = Field(default_factory=list)
    missing_certifications: list[str] = Field(default_factory=list)
    skill_coverage_percentage: float = Field(ge=0, le=100)
    project_coverage_percentage: float = Field(ge=0, le=100)
    experience_match: bool
    education_match: bool
