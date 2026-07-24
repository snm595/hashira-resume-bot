"""Deterministic learning recommendations based on missing skills."""

from pydantic import BaseModel, ConfigDict, Field


class CourseRecommendation(BaseModel):
    """One actionable recommendation for a missing capability."""

    model_config = ConfigDict(extra="forbid", strict=True)

    course_name: str
    provider: str
    difficulty: str
    duration: str
    priority: int = Field(ge=1)
    reason: str


class RecommendationEngine:
    """Map missing skills to a stable catalog without external API calls."""

    _CATALOG = {
        "python": ("Python for Everybody", "Coursera", "Beginner", "8 weeks"),
        "sql": ("SQL for Data Science", "Coursera", "Beginner", "4 weeks"),
        "excel": ("Excel Skills for Business", "Coursera", "Beginner", "6 weeks"),
        "java": ("Java Programming", "Coursera", "Beginner", "5 weeks"),
        "docker": ("Docker Essentials", "IBM SkillsBuild", "Beginner", "6 hours"),
        "aws": ("AWS Cloud Practitioner Essentials", "AWS Skill Builder", "Beginner", "6 hours"),
        "react": ("Front-End Development with React", "Coursera", "Intermediate", "4 weeks"),
        "mongodb": ("MongoDB Basics", "MongoDB University", "Beginner", "3 weeks"),
        "r": ("Data Science: R Basics", "edX", "Beginner", "8 weeks"),
        "sas": ("SAS Programmer Professional Certificate", "Coursera", "Beginner", "2 months"),
        "vba": ("Excel VBA Programming", "Udemy", "Beginner", "4 weeks"),
        "kubernetes": ("Introduction to Kubernetes", "Linux Foundation", "Beginner", "14 hours"),
    }

    def recommend(self, missing_skills: list[str], limit: int = 3) -> list[CourseRecommendation]:
        """Return deterministic high-priority recommendations in missing-skill order."""
        recommendations: list[CourseRecommendation] = []
        for skill in missing_skills[:limit]:
            course_name, provider, difficulty, duration = self._CATALOG.get(
                skill.casefold(),
                (f"Foundations of {skill}", "Coursera", "Beginner", "Self-paced"),
            )
            recommendations.append(
                CourseRecommendation(
                    course_name=course_name,
                    provider=provider,
                    difficulty=difficulty,
                    duration=duration,
                    priority=len(recommendations) + 1,
                    reason=f"Builds the missing job requirement: {skill}.",
                )
            )
        return recommendations
