"""Strict models produced by the deterministic scoring engine."""

from pydantic import BaseModel, ConfigDict, Field


class SectionScores(BaseModel):
    """Weighted score contribution from each screening section."""

    model_config = ConfigDict(extra="forbid", strict=True)

    technical_skills: float = Field(ge=0)
    projects: float = Field(ge=0)
    experience: float = Field(ge=0)
    education: float = Field(ge=0)
    certifications: float = Field(ge=0)


class CandidateScore(BaseModel):
    """A fully Python-calculated candidate score and human-readable breakdown."""

    model_config = ConfigDict(extra="forbid", strict=True)

    candidate_name: str
    overall_score: float = Field(ge=0, le=100)
    section_scores: SectionScores
    confidence_score: float = Field(ge=0, le=100)
    score_explanation: list[str] = Field(default_factory=list)
