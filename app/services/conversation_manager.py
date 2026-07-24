"""Application-scoped conversation state for the upload workflow."""

from pathlib import Path
from app.models.upload import ConversationState, UploadMetadata, UploadSession
from app.services.upload_service import UploadService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ConversationStateManager:
    """Owns upload sessions without relying on module-level session state."""

    def __init__(self, upload_service: UploadService) -> None:
        self._upload_service = upload_service
        self._sessions: dict[int, UploadSession] = {}

    def start_session(self, user_id: int) -> UploadSession:
        """Discard a user's prior temporary files and begin awaiting a JD."""
        previous_session = self._sessions.get(user_id)
        if previous_session is not None:
            self._log_report_counts("Session reset before /start or /newjd", previous_session)
        self._upload_service.cleanup_session(user_id)
        session = UploadSession(
            user_id=user_id,
            report_batch_id=(previous_session.report_batch_id + 1) if previous_session else 0,
        )
        self._sessions[user_id] = session
        self._log_report_counts("Session reset after /start or /newjd", session)
        return session

    def get_session(self, user_id: int) -> UploadSession | None:
        """Return a user's active session, if they started one."""
        return self._sessions.get(user_id)

    def record_job_description(self, user_id: int, upload: UploadMetadata) -> UploadSession:
        """Store the only JD and advance the session to resume collection."""
        session = self._require_session(user_id)
        session.job_description = upload
        session.state = ConversationState.WAITING_FOR_RESUMES
        return session

    def record_resume(self, user_id: int, upload: UploadMetadata) -> UploadSession:
        """Start a fresh batch when needed, then append the uploaded resume."""
        session = self._require_session(user_id)
        if self.has_screening_results(user_id):
            self.reset_resumes_keep_jd(user_id)
            session = self._require_session(user_id)
            logger.info("Started a new resume batch for user_id=%d", user_id)
        session.resumes.append(upload)
        session.state = ConversationState.READY_TO_PROCESS
        return session

    def has_screening_results(self, user_id: int) -> bool:
        """Return whether the current resumes have reports that must remain viewable."""
        session = self._require_session(user_id)
        return any(
            (
                session.comparisons,
                session.candidate_scores,
                session.candidate_evaluations,
                session.course_recommendations,
                session.ranked_candidates,
            )
        )

    def can_accept_resume(self, user_id: int, maximum: int) -> bool:
        """Check the configured resume limit before downloading another document."""
        session = self._require_session(user_id)
        return len(session.resumes) < maximum

    def reset_session(self, user_id: int) -> None:
        """Remove one user's state and corresponding temporary upload directory."""
        session = self._sessions.get(user_id)
        if session is not None:
            self._log_report_counts("Session reset before /reset", session)
        self._upload_service.cleanup_session(user_id)
        self._sessions.pop(user_id, None)
        logger.debug("Session reset after /reset: comparisons=0 scores=0 evals=0 recs=0 rankings=0")

    def reset_resumes_keep_jd(self, user_id: int) -> None:
        """Clear uploaded resume files and reset session state, keeping Job Description."""
        session = self.get_session(user_id)
        if session:
            self._log_report_counts("Session reset before new resume batch", session)
            for resume in session.resumes:
                try:
                    p = Path(resume.file_path)
                    if p.exists():
                        p.unlink()
                except Exception as e:
                    logger.warning("Error removing temporary resume file %s: %s", resume.file_path, e)
            session.reset_for_next_batch()
            self._log_report_counts("Session reset after new resume batch", session)

    @staticmethod
    def _log_report_counts(event: str, session: UploadSession) -> None:
        logger.debug(
            "%s: comparisons=%d scores=%d evals=%d recs=%d rankings=%d",
            event,
            len(session.comparisons),
            len(session.candidate_scores),
            len(session.candidate_evaluations),
            len(session.course_recommendations),
            len(session.ranked_candidates),
        )

    def _require_session(self, user_id: int) -> UploadSession:
        session = self.get_session(user_id)
        if session is None:
            raise ValueError("No active upload session. Send /start first.")
        return session
