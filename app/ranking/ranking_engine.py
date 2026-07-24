"""Stable candidate ordering based only on deterministic Python scores."""

from pydantic import BaseModel, ConfigDict, Field

from app.comparison.comparison_models import ResumeComparisonResult
from app.scoring.score_models import CandidateScore


class RankedCandidate(BaseModel):
    """The compact ranking data needed for recruiter summaries."""

    model_config = ConfigDict(extra="forbid", strict=True)

    rank: int = Field(ge=1)
    candidate_name: str
    overall_score: float = Field(ge=0, le=100)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    candidate_index: int = Field(ge=0)


class RankingEngine:
    """Rank score/comparison pairs with stable uploaded-resume tie-breaking."""

    def rank(
        self,
        scores: list[CandidateScore],
        comparisons: list[ResumeComparisonResult],
    ) -> list[RankedCandidate]:
        """Sort descending by score, preserving original upload order for ties."""
        if len(scores) != len(comparisons):
            raise ValueError("Scores and comparisons must have the same length.")
        ordered_indices = sorted(range(len(scores)), key=lambda index: -scores[index].overall_score)
        return [
            RankedCandidate(
                rank=rank,
                candidate_name=scores[index].candidate_name,
                overall_score=scores[index].overall_score,
                matched_skills=comparisons[index].matched_skills,
                missing_skills=comparisons[index].missing_skills,
                candidate_index=index,
            )
            for rank, index in enumerate(ordered_indices, start=1)
        ]
