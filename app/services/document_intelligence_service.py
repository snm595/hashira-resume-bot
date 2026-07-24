"""Orchestration of parsing, normalization, and structured AI extraction."""

import asyncio
from time import perf_counter
from typing import Awaitable, Callable, Optional

from app.extractor.jd_extractor import JobDescriptionExtractor
from app.extractor.resume_extractor import ResumeExtractor
from app.models.document import NormalizedDocument, ParsedDocument
from app.models.upload import UploadSession
from app.normalizer.document_normalizer import DocumentNormalizer
from app.parser.parser_factory import ParserFactory
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentIntelligenceService:
    """Produce and store structured documents for one completed upload session."""

    def __init__(

        self,
        parser_factory: ParserFactory,
        normalizer: DocumentNormalizer,
        jd_extractor: JobDescriptionExtractor,
        resume_extractor: ResumeExtractor,
    ) -> None:
        self._parser_factory = parser_factory
        self._normalizer = normalizer
        self._jd_extractor = jd_extractor
        self._resume_extractor = resume_extractor

    async def process(
        self,
        session: UploadSession,
        progress_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> int:
        """Process a session atomically with progress callbacks and concurrency."""
        if session.job_description is None or not session.resumes:
            raise ValueError("A job description and at least one resume are required.")

        # Stage 1: Parsing documents
        if progress_callback:
            await progress_callback("📄 Parsing documents...")

        parse_start = perf_counter()

        parsed_jd, normalized_jd = await self._parse_and_normalize(session.job_description.file_path)

        resume_parse_tasks = [
            self._parse_and_normalize(resume.file_path) for resume in session.resumes
        ]
        parsed_and_norm_resumes = await asyncio.gather(*resume_parse_tasks)

        parsed_resumes = [p for p, _ in parsed_and_norm_resumes]
        normalized_resumes = [n for _, n in parsed_and_norm_resumes]

        parsing_duration = perf_counter() - parse_start
        logger.info("Parsing completed in %.3fs (parsing_time=%.3fs) for 1 JD and %d resumes", parsing_duration, parsing_duration, len(session.resumes))

        # Stage 2: Extracting structured data
        if progress_callback:
            await progress_callback("🧠 Extracting structured data...")

        extract_start = perf_counter()

        jd_extract_task = asyncio.to_thread(self._jd_extractor.extract, normalized_jd)
        resume_extract_tasks = [
            asyncio.to_thread(self._resume_extractor.extract, norm)
            for norm in normalized_resumes
        ]

        results = await asyncio.gather(jd_extract_task, *resume_extract_tasks)
        extracted_jd = results[0]
        extracted_resumes = list(results[1:])

        extraction_duration = perf_counter() - extract_start
        logger.info("Extraction completed in %.3fs (extraction_time=%.3fs) for 1 JD and %d resumes", extraction_duration, extraction_duration, len(extracted_resumes))

        session.parsed_job_description = parsed_jd
        session.normalized_job_description = normalized_jd
        session.extracted_job_description = extracted_jd
        session.parsed_resumes = parsed_resumes
        session.normalized_resumes = normalized_resumes
        session.extracted_resumes = extracted_resumes
        return len(extracted_resumes)

    async def _parse_and_normalize(self, file_path: str) -> tuple[ParsedDocument, NormalizedDocument]:
        parser = self._parser_factory.get_parser(file_path)
        parsed = await asyncio.to_thread(parser.parse, file_path)
        return parsed, await asyncio.to_thread(self._normalizer.normalize, parsed)
