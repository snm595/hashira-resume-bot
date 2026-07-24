# app/llm/__init__.py
"""
LLM Client package.

Provides an abstracted interface to LLM providers (Phase 4):

Provider Strategy:
    - Primary: Google Gemini API via google-genai SDK.
    - Fallback: OpenRouter via OpenAI-compatible API (openai SDK).

    The fallback activates automatically when the primary provider
    fails (timeout, rate limit, API error). This ensures the bot
    remains responsive even during Gemini API outages.

Responsibilities:
    - API communication with retry and error handling.
    - JSON mode enforcement (PRD §12).
    - Temperature 0 for deterministic outputs.
    - Provider-agnostic interface so callers don't know which backend is used.

Separation of Concerns:
    - Prompt construction lives in the prompts package.
    - Business logic lives in the extractor and scoring packages.
    - This package handles ONLY the LLM API communication layer.
"""
