# app/extractor/__init__.py
"""
Information Extractor package.

Uses LLM to extract structured data from parsed text:
- Resume field extraction (Phase 4)
- JD requirement extraction (Phase 4)

Output is always validated Pydantic models, never raw strings.
"""
