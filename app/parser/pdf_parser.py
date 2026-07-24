"""PDF text extraction using PyMuPDF."""

import hashlib
from pathlib import Path

import fitz
from pydantic import ValidationError

from app.models.document import ParsedDocument
from app.parser.base_parser import BaseParser, ParserException


class PDFParser(BaseParser):
    """Extract text from every PDF page while retaining page boundaries."""

    def parse(self, file_path: str | Path) -> ParsedDocument:
        """Return raw PDF text, page count, source metadata, and SHA-256 hash."""
        path = Path(file_path)
        try:
            content = path.read_bytes()
            with fitz.open(stream=content, filetype="pdf") as document:
                page_text = [page.get_text("text") for page in document]
                metadata = {
                    key: value
                    for key, value in document.metadata.items()
                    if value is not None and value != ""
                }
                metadata["format"] = "pdf"
                metadata["page_count"] = document.page_count
                return ParsedDocument(
                    filename=path.name,
                    pages=document.page_count,
                    raw_text="\n\f\n".join(page_text),
                    metadata=metadata,
                    file_hash=hashlib.sha256(content).hexdigest(),
                )
        except (OSError, fitz.FileDataError, RuntimeError, ValueError, ValidationError) as error:
            raise ParserException(f"Unable to parse PDF '{path.name}'.") from error
