"""Models used by the Phase 2 upload and conversation workflow."""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from app.models.document import (
    ExtractedJobDescription,
    ExtractedResume,
    NormalizedDocument,
    ParsedDocument,
)
from app.comparison.comparison_models import ResumeComparisonResult
from app.extractor.resume_evaluator import CandidateEvaluation
from app.ranking.ranking_engine import RankedCandidate
from app.recommendation.recommendation_engine import CourseRecommendation
from app.scoring.score_models import CandidateScore
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ConversationState(str, Enum):
    """The three stages a user can occupy during an upload session."""

    WAITING_FOR_JD = "waiting_for_jd"
    WAITING_FOR_RESUMES = "waiting_for_resumes"
    READY_TO_PROCESS = "ready_to_process"


class UploadType(str, Enum):
    """The role an uploaded document has in a screening session."""

    JOB_DESCRIPTION = "job_description"
    RESUME = "resume"


class UploadMetadata(BaseModel):
    """Persistent-in-session facts about one stored upload."""

    original_filename: str
    stored_filename: str
    upload_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    mime_type: str
    size: int = Field(ge=0)
    file_path: str
    upload_type: UploadType
    telegram_file_id: str


class UploadSession(BaseModel):
    """All upload state belonging to a single Telegram user."""

    user_id: int
    state: ConversationState = ConversationState.WAITING_FOR_JD
    job_description: UploadMetadata | None = None
    resumes: list[UploadMetadata] = Field(default_factory=list)
    parsed_job_description: ParsedDocument | None = None
    normalized_job_description: NormalizedDocument | None = None
    extracted_job_description: ExtractedJobDescription | None = None
    parsed_resumes: list[ParsedDocument] = Field(default_factory=list)
    normalized_resumes: list[NormalizedDocument] = Field(default_factory=list)
    extracted_resumes: list[ExtractedResume] = Field(default_factory=list)
    comparisons: list[ResumeComparisonResult] = Field(default_factory=list)
    candidate_scores: list[CandidateScore] = Field(default_factory=list)
    candidate_evaluations: list[CandidateEvaluation] = Field(default_factory=list)
    course_recommendations: list[list[CourseRecommendation]] = Field(default_factory=list)
    ranked_candidates: list[RankedCandidate] = Field(default_factory=list)
    report_batch_id: int = Field(default=0, ge=0)

    def reset_for_next_batch(self) -> None:
        """Clear resumes, results, scores, rankings, but keep Job Description."""
        logger.debug(
            "Session reset_for_next_batch before: comparisons=%d scores=%d evals=%d recs=%d rankings=%d",
            len(self.comparisons),
            len(self.candidate_scores),
            len(self.candidate_evaluations),
            len(self.course_recommendations),
            len(self.ranked_candidates),
        )
        self.resumes = []
        self.parsed_resumes = []
        self.normalized_resumes = []
        self.extracted_resumes = []
        self.comparisons = []
        self.candidate_scores = []
        self.candidate_evaluations = []
        self.course_recommendations = []
        self.ranked_candidates = []
        self.report_batch_id += 1
        self.state = ConversationState.WAITING_FOR_RESUMES
        logger.debug(
            "Session reset_for_next_batch after: comparisons=%d scores=%d evals=%d recs=%d rankings=%d",
            len(self.comparisons),
            len(self.candidate_scores),
            len(self.candidate_evaluations),
            len(self.course_recommendations),
            len(self.ranked_candidates),
        )
