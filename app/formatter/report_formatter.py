"""Telegram-safe plain-text recruiter reports."""

from time import perf_counter

from app.comparison.comparison_models import ResumeComparisonResult
from app.extractor.resume_evaluator import CandidateEvaluation
from app.ranking.ranking_engine import RankedCandidate
from app.recommendation.recommendation_engine import CourseRecommendation
from app.scoring.score_models import CandidateScore
from app.utils.logger import get_logger

logger = get_logger(__name__)


SOFT_SKILLS = {
    "communication", "leadership", "teamwork", "problem solving", "critical thinking",
    "time management", "adaptability", "collaboration", "creativity", "work ethic",
    "interpersonal skills", "flexibility", "conflict resolution", "negotiation",
    "emotional intelligence", "decision making", "management", "organization", "patience"
}


def is_valid_skill(skill: str) -> bool:
    """Filter out complete sentences or excessively long phrases."""
    if not skill or len(skill.strip()) > 40:
        return False
    words = skill.strip().split()
    if len(words) > 5:
        return False
    if any(p in skill for p in [".", ";", "!", "?"]):
        return False
    return True


def is_soft_skill(skill: str) -> bool:
    """Check if skill is a soft skill."""
    s = skill.strip().lower()
    return s in SOFT_SKILLS or any(ws in s for ws in ["communication", "leadership", "teamwork", "collaboration", "interpersonal"])


class ReportFormatter:
    """Format stored screening results without implementing screening logic."""

    def summary_report(self, rankings: list[RankedCandidate]) -> str:
        """Return a concise rankings message for Telegram."""
        started_at = perf_counter()
        lines = ["🏆 Candidate Rankings", ""]
        lines.extend(
            f"{candidate.rank}. {candidate.candidate_name} — {candidate.overall_score:.0f}"
            for candidate in rankings
        )
        report = "\n".join(lines)
        logger.info("Summary report generated in %.3fs", perf_counter() - started_at)
        return report

    def detailed_candidate_report(
        self,
        score: CandidateScore,
        comparison: ResumeComparisonResult,
        evaluation: CandidateEvaluation,
        recommendations: list[CourseRecommendation],
    ) -> str:
        """Return a recruiter-friendly detailed report for one candidate."""
        started_at = perf_counter()
        sections = score.section_scores

        matched_tech = [s for s in comparison.matched_skills if is_valid_skill(s) and not is_soft_skill(s)]
        missing_tech = [s for s in comparison.missing_skills if is_valid_skill(s) and not is_soft_skill(s)]
        missing_soft = [s for s in comparison.missing_skills if is_valid_skill(s) and is_soft_skill(s)]
        additional = [s for s in comparison.additional_skills if is_valid_skill(s)]

        lines = [
            f"Candidate: {score.candidate_name}",
            f"Overall Score: {score.overall_score:.0f}/100",
            f"Confidence: {score.confidence_score:.0f}%",
            "",
            "Section Breakdown",
            f"• Technical Skills: {sections.technical_skills:.0f}",
            f"• Projects: {sections.projects:.0f}",
            f"• Experience: {sections.experience:.0f}",
            f"• Education: {sections.education:.0f}",
            f"• Certifications: {sections.certifications:.0f}",
            "",
            f"Matched Technical Skills: {', '.join(matched_tech) or 'None'}",
            f"Missing Technical Skills: {', '.join(missing_tech) or 'None'}",
            f"Missing Soft Skills: {', '.join(missing_soft) or 'None'}",
            f"Additional Skills: {', '.join(additional) or 'None'}",
            f"Strengths: {'; '.join(evaluation.strengths) or 'None'}",
            f"Weaknesses: {'; '.join(evaluation.weaknesses) or 'None'}",
            f"Interview Readiness: {evaluation.interview_readiness or 'Not specified'}",
            f"Hiring Recommendation: {evaluation.hiring_recommendation or 'Not specified'}",
            "Recommended Courses:",
        ]
        lines.extend(
            f"{course.priority}. {course.course_name} ({course.provider}) — {course.reason}"
            for course in recommendations
        )
        report = "\n".join(lines)
        logger.info("Detailed candidate report generated in %.3fs", perf_counter() - started_at)
        return report
