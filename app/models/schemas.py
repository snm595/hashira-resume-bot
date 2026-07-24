"""
Core Pydantic models (schemas) for the application.

Design Decision:
    All data structures shared between layers are defined here as Pydantic
    models. This provides:
    1. Type safety — every field is validated at construction.
    2. Serialization — easy JSON conversion for API responses.
    3. Documentation — field descriptions serve as inline docs.
    4. Immutability — frozen models prevent accidental mutation.

    Models are organized by domain concern. As the application grows,
    this file can be split into sub-modules (e.g., models/resume.py,
    models/job_description.py) while keeping the same import path
    via __init__.py re-exports.

    We define only the models needed for Phase 1 here. Future phases
    will add ExtractedResume, ExtractedJD, CandidateScore, etc.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ===========================================================================
# Enums
# ===========================================================================


class ConversationState(str, Enum):
    """
    Tracks where a user is in the conversation flow.

    The bot guides users through a strict sequence:
    IDLE → AWAITING_JD → AWAITING_RESUMES → READY_TO_PROCESS → PROCESSING → COMPLETED

    Design Decision:
        Using str Enum so the state is human-readable in logs and
        can be serialized to JSON without custom encoders.
    """

    IDLE = "idle"
    AWAITING_JD = "awaiting_jd"
    AWAITING_RESUMES = "awaiting_resumes"
    READY_TO_PROCESS = "ready_to_process"
    PROCESSING = "processing"
    COMPLETED = "completed"


class DocumentType(str, Enum):
    """
    Classifies an uploaded document as either a Job Description or a Resume.
    """

    JOB_DESCRIPTION = "job_description"
    RESUME = "resume"


# ===========================================================================
# Document Models
# ===========================================================================


class DocumentMetadata(BaseModel):
    """
    Metadata for an uploaded document.

    Captures essential information about a file without storing its content
    in memory. The actual file is stored on disk at `file_path`.

    Attributes:
        file_id: Telegram file_id for re-downloading if needed.
        file_name: Original filename as uploaded by the user.
        file_path: Local filesystem path where the file is saved.
        file_size_bytes: File size in bytes.
        mime_type: MIME type (e.g., application/pdf).
        document_type: Whether this is a JD or resume.
        uploaded_at: Timestamp when the file was received.
    """

    file_id: str = Field(description="Telegram file_id")
    file_name: str = Field(description="Original filename")
    file_path: str = Field(description="Local filesystem path to saved file")
    file_size_bytes: int = Field(ge=0, description="File size in bytes")
    mime_type: str = Field(description="MIME type of the document")
    document_type: DocumentType = Field(description="JD or Resume classification")
    uploaded_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of upload",
    )


# ===========================================================================
# Session Models
# ===========================================================================


class SessionData(BaseModel):
    """
    In-memory session state for a single Telegram chat.

    Each chat_id maps to one SessionData instance. This tracks the
    conversation state and all uploaded documents for that session.

    Design Decision:
        We store sessions in-memory (dict[int, SessionData]) rather than
        a database for the MVP. This is acceptable because:
        1. Sessions are ephemeral — cleared on /reset or bot restart.
        2. No permanent resume storage (PRD §7 Security).
        3. A database adds complexity without MVP value.

        Future: If persistence is needed, this model can be serialized
        to Redis or SQLite with zero changes to the interface.

    Attributes:
        chat_id: Telegram chat identifier.
        state: Current conversation state.
        job_description: Metadata for the uploaded JD (None if not yet uploaded).
        resumes: List of metadata for uploaded resumes.
        created_at: When this session was initialized.
    """

    chat_id: int = Field(description="Telegram chat identifier")
    state: ConversationState = Field(
        default=ConversationState.IDLE,
        description="Current conversation state",
    )
    job_description: DocumentMetadata | None = Field(
        default=None,
        description="Uploaded job description metadata",
    )
    resumes: list[DocumentMetadata] = Field(
        default_factory=list,
        description="List of uploaded resume metadata",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Session creation timestamp",
    )


# ===========================================================================
# API Response Models
# ===========================================================================


class HealthResponse(BaseModel):
    """
    Response model for the /health endpoint.

    Provides a quick status check for monitoring and load balancers.

    Attributes:
        status: Service health status string.
        version: Application version.
        timestamp: Current server time.
    """

    status: str = Field(default="healthy", description="Service health status")
    version: str = Field(default="1.0.0", description="Application version")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Current server timestamp",
    )
