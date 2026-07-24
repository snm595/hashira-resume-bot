"""Provider-neutral JSON generation with Gemini primary and OpenRouter fallback."""

import asyncio
import json
import re
import time
from collections.abc import Iterator
from typing import Any

from google import genai
from google.genai import types
from openai import OpenAI

from app.config.settings import Settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LLMGenerationError(RuntimeError):
    """Raised when neither configured LLM provider produces valid JSON."""


class LLMClient:
    """Keep provider details behind one strict-JSON generation interface."""

    def __init__(self, app_settings: Settings) -> None:
        self._settings = app_settings
        self._gemini_client = genai.Client(api_key=app_settings.gemini_api_key)
        self._gemini_semaphore = asyncio.Semaphore(app_settings.gemini_max_concurrent_requests)
        self._openrouter_client = (
            OpenAI(api_key=app_settings.openrouter_api_key, base_url=app_settings.openrouter_base_url)
            if app_settings.fallback_enabled
            else None
        )

    async def generate_json_async(self, prompt: str) -> dict[str, object]:
        """Generate JSON while limiting concurrent Gemini request workflows."""
        async with self._gemini_semaphore:
            return await asyncio.to_thread(self.generate_json, prompt)

    def generate_json(self, prompt: str) -> dict[str, object]:
        """Generate JSON with retryable Gemini model fallback, then OpenRouter fallback."""
        try:
            return self._generate_with_gemini_models(prompt)
        except Exception as primary_error:
            logger.warning("Gemini extraction failed across all models: %s", primary_error)
            if not self._is_retryable_availability_error(primary_error):
                raise LLMGenerationError("Gemini extraction failed with a non-retryable error.") from primary_error
            if self._openrouter_client is None:
                logger.warning(
                    "No provider fallback is configured; returning empty qualitative evaluation after all Gemini models failed."
                )
                return {}
            try:
                logger.info("Switching to OpenRouter fallback provider model '%s'", self._settings.openrouter_model)
                result = self._generate_with_openrouter(prompt)
                logger.info("Final model used: '%s' (after Gemini fallback chain)", self._settings.openrouter_model)
                return result
            except Exception as fallback_error:
                logger.warning(
                    "OpenRouter fallback failed after all Gemini models; returning empty qualitative evaluation: %s",
                    fallback_error,
                )
                return {}

    def _generate_with_gemini_models(self, prompt: str) -> dict[str, object]:
        """Try the configured model followed by ordered alternatives for availability errors."""
        raw_fallbacks = self._settings.gemini_model_fallbacks
        if isinstance(raw_fallbacks, str):
            fallbacks = [m.strip() for m in raw_fallbacks.split(",") if m.strip()]
        else:
            fallbacks = list(raw_fallbacks)

        models = list(dict.fromkeys([self._settings.gemini_model, *fallbacks]))
        last_error: Exception | None = None
        attempts = [0]

        for index, model in enumerate(models):
            try:
                logger.info("Gemini model activated (%d/%d): '%s'", index + 1, len(models), model)
                result = self._generate_with_gemini(prompt, model, attempts)
                logger.info(
                    "Gemini final model used: '%s' (total API attempts: %d)", model, attempts[0]
                )
                return result
            except Exception as error:
                if self._is_model_unavailable_error(error):
                    last_error = error
                    logger.warning("Gemini model skipped as unavailable: '%s' (%s)", model, error)
                elif self._is_retryable_availability_error(error):
                    last_error = error
                    logger.warning("Gemini model skipped after retryable failure: '%s' (%s)", model, error)
                else:
                    logger.error("Non-retryable error encountered on model '%s': %s", model, error)
                    raise
                if index < len(models) - 1:
                    logger.info("Attempting next configured Gemini model: '%s'", models[index + 1])

        if last_error is None:
            raise LLMGenerationError("No Gemini model is configured.")
        logger.warning("All configured Gemini models failed (total API attempts: %d)", attempts[0])
        raise last_error

    def _generate_with_gemini(
        self, prompt: str, model: str, attempts: list[int] | None = None
    ) -> dict[str, object]:
        """Retry one Gemini model with 1s, 2s, and 4s exponential backoff."""
        delays = (1, 2, 4)
        for attempt, delay in enumerate(delays, start=1):
            try:
                if attempts is not None:
                    attempts[0] += 1
                return self._request_gemini(prompt, model)
            except Exception as error:
                if self._is_model_unavailable_error(error):
                    raise
                if not self._is_retryable_availability_error(error) or attempt == len(delays):
                    raise
                retry_delay = self._retry_info_delay(error)
                if retry_delay is None:
                    retry_delay = delay
                    delay_source = "exponential"
                else:
                    delay_source = "RetryInfo"
                logger.warning(
                    "Gemini API error on model '%s' (attempt %d/%d). Retrying in %ss "
                    "using %s delay. Error: %s",
                    model,
                    attempt,
                    len(delays),
                    retry_delay,
                    delay_source,
                    error,
                )
                time.sleep(retry_delay)
        raise LLMGenerationError("Gemini retry loop ended unexpectedly.")

    def _request_gemini(self, prompt: str, model: str) -> dict[str, object]:
        config_options: dict[str, object] = {
            "max_output_tokens": self._settings.gemini_max_tokens,
            "response_mime_type": "application/json",
        }
        if not model.startswith("gemini-3."):
            config_options["temperature"] = self._settings.gemini_temperature
        response = self._gemini_client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(**config_options),
        )
        return self._decode_json(response.text)

    @staticmethod
    def _is_retryable_availability_error(error: Exception) -> bool:
        """Limit retries and model fallback to transient capacity or availability errors."""
        if LLMClient._is_model_unavailable_error(error):
            return True
        code = getattr(error, "code", None) or getattr(error, "status_code", None)
        if code in {429, 503}:
            return True
        message = str(error).casefold()
        return any(
            marker in message
            for marker in (
                "429",
                "503",
                "unavailable",
                "high demand",
                "overloaded",
                "model not found",
                "resource exhausted",
                "rate limit",
                "quota",
            )
        )

    @staticmethod
    def _is_model_unavailable_error(error: Exception) -> bool:
        """Return whether Gemini rejected a model because it is unavailable."""
        code = getattr(error, "code", None) or getattr(error, "status_code", None)
        try:
            is_404 = int(code) == 404
        except (TypeError, ValueError):
            is_404 = False
        message = str(error).casefold()
        return is_404 or "404" in message or "not_found" in message

    @classmethod
    def _retry_info_delay(cls, error: Exception) -> float | None:
        """Extract the protobuf RetryInfo retryDelay, expressed in seconds."""
        details = getattr(error, "details", None)
        for item in cls._walk_error_details(details):
            if not isinstance(item, dict):
                continue
            type_name = str(item.get("@type", ""))
            retry_delay = item.get("retryDelay")
            if retry_delay is not None and ("RetryInfo" in type_name or len(item) == 1):
                return cls._parse_protobuf_duration(retry_delay)
        return None

    @staticmethod
    def _walk_error_details(value: Any) -> Iterator[Any]:
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from LLMClient._walk_error_details(child)
        elif isinstance(value, list):
            for child in value:
                yield from LLMClient._walk_error_details(child)

    @staticmethod
    def _parse_protobuf_duration(value: object) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))s", str(value).strip())
        if match is None:
            return None
        delay = float(match.group(1))
        return delay if delay >= 0 else None

    def _generate_with_openrouter(self, prompt: str) -> dict[str, object]:
        if self._openrouter_client is None:
            raise LLMGenerationError("OpenRouter fallback is not configured.")
        response = self._openrouter_client.chat.completions.create(
            model=self._settings.openrouter_model,
            temperature=self._settings.gemini_temperature,
            max_tokens=self._settings.gemini_max_tokens,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        return self._decode_json(response.choices[0].message.content)

    @staticmethod
    def _decode_json(content: str | None) -> dict[str, object]:
        if not content:
            raise LLMGenerationError("The provider returned an empty response.")
        payload = json.loads(content)
        if not isinstance(payload, dict):
            raise LLMGenerationError("The provider response was not a JSON object.")
        return payload
