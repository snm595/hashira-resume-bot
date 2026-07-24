"""Tests for resilient job-description response normalization."""

import unittest

from app.extractor.response_normalizer import ExtractionResponseNormalizer
from app.models.document import ExtractedJobDescription


class JobDescriptionResponseNormalizerTests(unittest.TestCase):
    """Keep strict JD validation while accepting harmless LLM shape variations."""

    def validate(self, payload: dict[str, object]) -> ExtractedJobDescription:
        return ExtractedJobDescription.model_validate(
            ExtractionResponseNormalizer.normalize_job_description(payload)
        )

    def test_experience_string_is_preserved(self) -> None:
        job_description = self.validate({"experience": "3+ years of Python experience"})

        self.assertEqual(job_description.experience, "3+ years of Python experience")

    def test_experience_list_becomes_readable_string(self) -> None:
        job_description = self.validate(
            {"experience": ["Previous internships", "Related project experience"]}
        )

        self.assertEqual(
            job_description.experience,
            "Previous internships; Related project experience",
        )

    def test_experience_null_becomes_optional_none(self) -> None:
        job_description = self.validate({"experience": None})

        self.assertIsNone(job_description.experience)

    def test_mixed_lists_nested_objects_and_duplicates_are_normalized(self) -> None:
        job_description = self.validate(
            {
                "technical_skills": ["Python", {"skill": "AWS", "level": "required"}, None, "python"],
                "soft_skills": "Communication",
                "education": {"degree": "BSc", "field": "Computer Science"},
                "certifications": ["AWS Certified", 123, "aws certified"],
                "responsibilities": [{"action": "Build APIs"}, None],
                "experience": {"minimum": "2 years", "focus": "backend"},
            }
        )

        self.assertEqual(job_description.required_skills, ["Python", "skill: AWS; level: required"])
        self.assertEqual(job_description.preferred_skills, ["Communication"])
        self.assertEqual(job_description.education, ["degree: BSc; field: Computer Science"])
        self.assertEqual(job_description.certifications, ["AWS Certified", "123"])
        self.assertEqual(job_description.responsibilities, ["action: Build APIs"])
        self.assertEqual(job_description.experience, "minimum: 2 years; focus: backend")

    def test_missing_fields_use_strict_schema_defaults(self) -> None:
        job_description = self.validate({})

        self.assertIsNone(job_description.experience)
        self.assertEqual(job_description.required_skills, [])
        self.assertEqual(job_description.education, [])


if __name__ == "__main__":
    unittest.main()
