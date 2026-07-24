"""LLM-backed, schema-validated job-description extraction."""

from pathlib import Path

from pydantic import ValidationError

from app.llm.client import LLMClient, LLMGenerationError
from app.extractor.response_normalizer import ExtractionResponseNormalizer
from app.models.document import ExtractedJobDescription, NormalizedDocument


class JobDescriptionExtractionError(RuntimeError):
    """Raised when JD data cannot be produced in the expected schema."""


class JobDescriptionExtractor:
    """Convert normalized job-description text into an ExtractedJobDescription model."""

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    def extract(self, document: NormalizedDocument) -> ExtractedJobDescription:
        """Send the document to the JSON-only prompt and validate the response."""
        try:
            payload = self._llm_client.generate_json(self._build_prompt(document.normalized_text))
            normalized_payload = ExtractionResponseNormalizer.normalize_job_description(payload)
            return ExtractedJobDescription.model_validate(normalized_payload)
        except (LLMGenerationError, ValidationError, ValueError) as error:
            raise JobDescriptionExtractionError(
                f"Could not extract structured data from '{document.filename}'."
            ) from error

    @staticmethod
    def _build_prompt(document_text: str) -> str:
        template = (Path(__file__).resolve().parents[1] / "prompts" / "jd_extraction.txt").read_text(encoding="utf-8")
        return template.replace("{{document_text}}", document_text)
