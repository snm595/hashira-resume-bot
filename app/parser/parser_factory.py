"""Format-to-parser selection for uploaded documents."""

from pathlib import Path

from app.parser.base_parser import BaseParser, ParserException
from app.parser.docx_parser import DocxParser
from app.parser.pdf_parser import PDFParser


class ParserFactory:
    """Creates the appropriate parser from a validated file extension."""

    def get_parser(self, file_path: str | Path) -> BaseParser:
        """Return the parser for a PDF or DOCX path, otherwise raise ParserException."""
        extension = Path(file_path).suffix.lower()
        if extension == ".pdf":
            return PDFParser()
        if extension == ".docx":
            return DocxParser()
        raise ParserException(f"No parser is available for '{extension or 'unknown'}' files.")
