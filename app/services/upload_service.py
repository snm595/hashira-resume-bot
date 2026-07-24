"""Safe temporary storage and validation for Telegram document uploads."""

from __future__ import annotations

import re
import shutil
import zipfile
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import fitz
from telegram import Bot, Document

from app.models.upload import UploadMetadata, UploadType


class UploadValidationError(ValueError):
    """Raised when an upload is not an acceptable PDF or DOCX document."""


class UploadService:
    """Validates documents and stores them in a private directory per user."""

    _ALLOWED_TYPES = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    _ALLOWED_DECLARED_MIME_TYPES = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",  # Telegram may not detect a MIME type.
    }

    def __init__(self, upload_dir: str | Path, max_file_size_bytes: int) -> None:
        """Configure the temporary storage root and maximum accepted size."""
        self._upload_dir = Path(upload_dir)
        self._max_file_size_bytes = max_file_size_bytes

    async def save_file(
        self,
        bot: Bot,
        document: Document,
        user_id: int,
        upload_type: UploadType,
    ) -> UploadMetadata:
        """Download, validate, and exclusively create a stored upload file."""
        original_filename = document.file_name or "unnamed"
        declared_size = document.file_size or 0
        if declared_size > self._max_file_size_bytes:
            raise UploadValidationError(self._size_error_message())

        telegram_file = await bot.get_file(document.file_id)
        content = bytes(await telegram_file.download_as_bytearray())
        mime_type = self.validate_file(
            original_filename=original_filename,
            declared_mime_type=document.mime_type,
            content=content,
        )

        user_directory = self._session_directory(user_id)
        user_directory.mkdir(parents=True, exist_ok=True)
        stored_filename = self.generate_safe_filename(original_filename)
        destination = user_directory / stored_filename
        # UUID names make collisions extremely unlikely; exclusive creation makes them impossible.
        while True:
            try:
                with destination.open("xb") as saved_file:
                    saved_file.write(content)
                break
            except FileExistsError:
                stored_filename = self.generate_safe_filename(original_filename)
                destination = user_directory / stored_filename

        return UploadMetadata(
            original_filename=Path(original_filename).name,
            stored_filename=stored_filename,
            mime_type=mime_type,
            size=len(content),
            file_path=str(destination),
            upload_type=upload_type,
            telegram_file_id=document.file_id,
        )

    def validate_file(
        self,
        original_filename: str,
        declared_mime_type: str | None,
        content: bytes,
    ) -> str:
        """Check size, extension, declared type, and the file's actual structure."""
        if not content:
            raise UploadValidationError("The uploaded file is empty or corrupted.")
        if len(content) > self._max_file_size_bytes:
            raise UploadValidationError(self._size_error_message())

        extension = Path(original_filename).suffix.lower()
        expected_mime_type = self._ALLOWED_TYPES.get(extension)
        if expected_mime_type is None:
            raise UploadValidationError("Only PDF and DOCX files are supported.")
        if (
            declared_mime_type
            and declared_mime_type.lower() not in self._ALLOWED_DECLARED_MIME_TYPES
        ):
            raise UploadValidationError("Only PDF and DOCX files are supported.")

        if extension == ".pdf":
            if not content.startswith(b"%PDF-") or b"%%EOF" not in content[-2048:]:
                raise UploadValidationError("This PDF appears to be corrupted or invalid.")
            try:
                # Opening the file verifies its PDF structure; no text or document data is read.
                with fitz.open(stream=content, filetype="pdf") as pdf:
                    _ = pdf.page_count
            except (fitz.FileDataError, RuntimeError, ValueError) as error:
                raise UploadValidationError("This PDF appears to be corrupted or invalid.") from error
        else:
            try:
                with zipfile.ZipFile(BytesIO(content)) as archive:
                    members = set(archive.namelist())
                    if "[Content_Types].xml" not in members or "word/document.xml" not in members:
                        raise UploadValidationError("This DOCX appears to be corrupted or invalid.")
                    archive.testzip()
            except (zipfile.BadZipFile, OSError, RuntimeError) as error:
                raise UploadValidationError("This DOCX appears to be corrupted or invalid.") from error
        return expected_mime_type

    def generate_safe_filename(self, original_filename: str) -> str:
        """Return a sanitized, unique filename while retaining its permitted extension."""
        source = Path(original_filename).name
        extension = Path(source).suffix.lower()
        stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(source).stem).strip("._")
        safe_stem = stem[:80] or "upload"
        return f"{safe_stem}_{uuid4().hex}{extension}"

    def cleanup_session(self, user_id: int) -> None:
        """Remove all temporary files for exactly one user's upload session."""
        session_directory = self._session_directory(user_id)
        if session_directory.exists():
            shutil.rmtree(session_directory)

    def _session_directory(self, user_id: int) -> Path:
        """Build a directory path only from a validated Telegram numeric user id."""
        if user_id <= 0:
            raise ValueError("user_id must be a positive Telegram user id")
        return self._upload_dir / str(user_id)

    def _size_error_message(self) -> str:
        max_mb = self._max_file_size_bytes // (1024 * 1024)
        return f"The file is too large. Maximum size is {max_mb} MB."
