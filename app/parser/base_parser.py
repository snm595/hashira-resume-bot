"""Shared interface and errors for document parsers."""

from abc import ABC, abstractmethod
from pathlib import Path

from app.models.document import ParsedDocument


class ParserException(Exception):
    """Raised when a supported file cannot be read into a ParsedDocument."""


class BaseParser(ABC):
    """A format-specific parser that always returns a complete parsed document."""

    @abstractmethod
    def parse(self, file_path: str | Path) -> ParsedDocument:
        """Read a document from disk or raise ParserException."""
