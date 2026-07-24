# app/prompts/__init__.py
"""
Prompt Templates package.

Contains all LLM prompt templates organized by function:
- Resume extraction (Phase 4)
- JD extraction (Phase 4)
- Evaluation (Phase 6)
- Course recommendation (Phase 6)

Design Decision:
    Prompts are separated from the LLM client to allow:
    1. Independent iteration on prompt quality.
    2. Version tracking of prompt changes.
    3. Easy A/B testing of different prompt strategies.
    4. Clear audit trail for prompt engineering decisions.
"""
