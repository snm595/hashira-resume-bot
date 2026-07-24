# app/scoring/__init__.py
"""
Scoring Engine package.

Implements deterministic, rule-based scoring (PRD §13):
- Skill matching (Phase 5)
- Weighted scoring engine (Phase 5)
- Configurable score weights (Phase 5)

The scoring engine NEVER asks the LLM for scores. It uses
a deterministic rule engine with the LLM providing reasoning only.
"""
