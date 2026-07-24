"""Deterministic cleanup of text extracted from resumes and job descriptions."""

import hashlib
import re
import unicodedata
from collections import Counter

from app.models.document import NormalizedDocument, ParsedDocument


class DocumentNormalizer:
    """Normalize presentation differences without changing document meaning."""

    _BULLETS = re.compile(r"[•·◦▪▫●○◆◇►‣]")
    _PAGE_NUMBER = re.compile(r"^\s*(?:page\s*)?\d+(?:\s*(?:of|/)\s*\d+)?\s*$", re.I)
    _MULTI_SPACE = re.compile(r"[ \t]+")
    _MULTI_BLANK_LINES = re.compile(r"\n{3,}")

    def normalize(self, document: ParsedDocument) -> NormalizedDocument:
        """Return canonical text and a deterministic SHA-256 hash for its contents."""
        pages = [self._normal_lines(page) for page in document.raw_text.split("\f")]
        repeated_edges = self._repeated_page_edges(pages)
        cleaned_pages = [
            self._remove_page_chrome(lines, repeated_edges)
            for lines in pages
        ]
        normalized_text = "\n\n".join(
            "\n".join(lines) for lines in cleaned_pages if lines
        ).strip()
        normalized_text = self._MULTI_BLANK_LINES.sub("\n\n", normalized_text)
        return NormalizedDocument(
            filename=document.filename,
            pages=document.pages,
            normalized_text=normalized_text,
            metadata=document.metadata,
            file_hash=hashlib.sha256(normalized_text.encode("utf-8")).hexdigest(),
        )

    def _normal_lines(self, page: str) -> list[str]:
        normalized = unicodedata.normalize("NFKC", page).replace("\r\n", "\n").replace("\r", "\n")
        normalized = self._BULLETS.sub("-", normalized)
        lines = [self._MULTI_SPACE.sub(" ", line).strip() for line in normalized.split("\n")]
        return [self._normalize_heading_capitalization(line) for line in lines]

    def _repeated_page_edges(self, pages: list[list[str]]) -> set[str]:
        edges: list[str] = []
        for lines in pages:
            nonempty = [line for line in lines if line]
            if len(nonempty) >= 2:
                edges.extend((nonempty[0], nonempty[-1]))
        counts = Counter(edge for edge in edges if not self._PAGE_NUMBER.match(edge))
        return {edge for edge, count in counts.items() if count >= 2}

    def _remove_page_chrome(self, lines: list[str], repeated_edges: set[str]) -> list[str]:
        return [
            line for line in lines
            if line and not self._PAGE_NUMBER.match(line) and line not in repeated_edges
        ]

    @staticmethod
    def _normalize_heading_capitalization(line: str) -> str:
        if line and len(line) <= 80 and line.isupper() and any(character.isalpha() for character in line):
            return line.title()
        return line
