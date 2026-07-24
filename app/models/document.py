"""Strict models produced by the document intelligence pipeline."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    """Reject unexpected LLM fields while allowing explicitly optional fields."""

    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class ParsedDocument(_StrictModel):
    """Raw text and source facts extracted from one uploaded document."""

    filename: str = Field(min_length=1)
    pages: int = Field(ge=1)
    raw_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    file_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class NormalizedDocument(_StrictModel):
    """Deterministically normalized text ready for AI extraction."""

    filename: str = Field(min_length=1)
    pages: int = Field(ge=1)
    normalized_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    file_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class Experience(_StrictModel):
    """One employment entry identified in a resume."""

    title: str | None = None
    company: str | None = None
    duration: str | None = None
    description: list[str] = Field(default_factory=list)


class Education(_StrictModel):
    """One education entry identified in a resume."""

    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    graduation_year: str | None = None


class Project(_StrictModel):
    """One project entry identified in a resume."""

    name: str | None = None
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)


class ExtractedResume(_StrictModel):
    """Validated structured representation of a candidate resume."""

    candidate_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    skills: list[str] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    cloud: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)


class ExtractedJobDescription(_StrictModel):
    """Validated structured representation of a job description."""

    job_title: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    experience: str | None = None
    education: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    location: str | None = None
