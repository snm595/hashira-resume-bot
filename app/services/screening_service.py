"""Business orchestration for deterministic Phase 4 resume screening."""

import asyncio
from time import perf_counter
from typing import Awaitable, Callable, Optional

from app.comparison.comparison_engine import ComparisonEngine
from app.comparison.comparison_models import ResumeComparisonResult
from app.extractor.resume_evaluator import CandidateEvaluation, ResumeEvaluator
from app.models.upload import UploadSession
from app.ranking.ranking_engine import RankedCandidate, RankingEngine
from app.recommendation.recommendation_engine import CourseRecommendation, RecommendationEngine
from app.scoring.score_models import CandidateScore
from app.scoring.scoring_engine import ScoringEngine
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ScreeningService:
    """Run comparison, scoring, qualitative evaluation, recommendations, and ranking."""

    def __init__(
        self,
        comparison_engine: ComparisonEngine,
        scoring_engine: ScoringEngine,
        resume_evaluator: ResumeEvaluator,
        recommendation_engine: RecommendationEngine,
        ranking_engine: RankingEngine,
    ) -> None:
        self._comparison_engine = comparison_engine
        self._scoring_engine = scoring_engine
        self._resume_evaluator = resume_evaluator
        self._recommendation_engine = recommendation_engine
        self._ranking_engine = ranking_engine

    async def screen(
        self,
        session: UploadSession,
        progress_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> list[RankedCandidate]:
        """Screen extracted documents with concurrent evaluations, timing metrics, and progress updates."""
        if session.extracted_job_description is None or not session.extracted_resumes:
            raise ValueError("Extracted job description and resumes are required before screening.")

        total_started = perf_counter()

        try:
            # Stage 3: Comparing resumes
            if progress_callback:
                await progress_callback("📊 Comparing resumes...")

            comparison_start = perf_counter()
            comparisons = [
                self._comparison_engine.compare(resume, session.extracted_job_description)
                for resume in session.extracted_resumes
            ]
            comparison_time = perf_counter() - comparison_start
            logger.info("Comparison completed for %d resumes (comparison_time=%.3fs)", len(comparisons), comparison_time)

            # Stage 4: Scoring resumes
            scoring_start = perf_counter()
            scores = [
                self._scoring_engine.score(comparison, resume)
                for comparison, resume in zip(comparisons, session.extracted_resumes, strict=True)
            ]
            scoring_time = perf_counter() - scoring_start
            logger.info("Scoring completed for %d resumes (scoring_time=%.3fs)", len(scores), scoring_time)

            # Stage 5: Ranking candidates
            if progress_callback:
                await progress_callback("🏆 Calculating rankings...")

            ranking_start = perf_counter()
            rankings = self._ranking_engine.rank(scores, comparisons)
            ranking_time = perf_counter() - ranking_start
            logger.info("Ranking completed for %d candidates (ranking_time=%.3fs)", len(rankings), ranking_time)

            # Stage 6: Qualitative evaluation (Concurrent LLM Tasks)
            if progress_callback:
                await progress_callback("✨ Generating AI insights...")

            eval_start = perf_counter()
            eval_tasks = [
                self._resume_evaluator.evaluate_async(
                    resume,
                    session.extracted_job_description,
                    comparison,
                )
                for resume, comparison in zip(session.extracted_resumes, comparisons, strict=True)
            ]
            
            raw_evaluations = await asyncio.gather(*eval_tasks, return_exceptions=True)
            evaluations: list[CandidateEvaluation] = []
            for res in raw_evaluations:
                if isinstance(res, Exception):
                    logger.error("Qualitative evaluation error (falling back to empty evaluation): %s", res)
                    evaluations.append(CandidateEvaluation())
                else:
                    evaluations.append(res)

            eval_time = perf_counter() - eval_start
            logger.info("Qualitative evaluation completed concurrently for %d resumes (qualitative_evaluation_time=%.3fs)", len(evaluations), eval_time)

            # Stage 7: Recommendations
            recommendation_start = perf_counter()
            recommendations = [
                self._recommendation_engine.recommend(comparison.missing_skills)
                for comparison in comparisons
            ]
            recommendation_time = perf_counter() - recommendation_start
            logger.info("Recommendations completed for %d resumes (recommendation_time=%.3fs)", len(recommendations), recommendation_time)

            total_screening_time = perf_counter() - total_started

            logger.info(
                "Pipeline Timings Summary:\n"
                "  - comparison_time: %.3fs\n"
                "  - scoring_time: %.3fs\n"
                "  - ranking_time: %.3fs\n"
                "  - qualitative_evaluation_time: %.3fs\n"
                "  - recommendation_time: %.3fs\n"
                "  - total_screening_time: %.3fs",
                comparison_time,
                scoring_time,
                ranking_time,
                eval_time,
                recommendation_time,
                total_screening_time,
            )

            session.comparisons = comparisons
            session.candidate_scores = scores
            session.candidate_evaluations = evaluations
            session.course_recommendations = recommendations
            session.ranked_candidates = rankings
            return rankings

        except Exception:
            logger.exception("Screening failed after %.3fs", perf_counter() - total_started)
            raise
