"""
Application settings loaded from environment variables.

Design Decision:
    We use Pydantic's BaseSettings instead of raw os.getenv() because:
    1. Type validation — catches misconfiguration at startup, not at runtime.
    2. Default values — documented in one place, not scattered across modules.
    3. .env file support — via python-dotenv integration.
    4. Immutability — settings are frozen after initialization.

    This is the SINGLE SOURCE OF TRUTH for all configuration.
    No module should read environment variables directly.

LLM Provider Strategy:
    - Primary: Google Gemini API (via google-genai SDK).
    - Fallback: OpenRouter (via OpenAI-compatible API using openai SDK).

    OpenRouter is used as a fallback because:
    1. It provides access to the same Gemini models via a different route.
    2. If Gemini's API is rate-limited or down, OpenRouter can step in.
    3. It uses the OpenAI SDK with a custom base_url, so no new dependency.

Usage:
    from app.config.settings import settings
    token = settings.telegram_bot_token
"""

from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application-wide settings, loaded from .env file and environment variables.

    Attributes:
        telegram_bot_token: Telegram Bot API token from @BotFather.
        gemini_api_key: Google Gemini API key (primary LLM provider).
        gemini_model: Gemini model identifier (e.g., gemini-2.5-flash).
        gemini_temperature: LLM temperature. 0.0 for deterministic output.
        gemini_max_tokens: Maximum tokens per LLM response.
        openrouter_api_key: OpenRouter API key (fallback LLM provider).
        openrouter_model: Model identifier on OpenRouter.
        openrouter_base_url: OpenRouter API base URL.
        log_level: Python logging level.
        upload_dir: Directory for temporary file uploads.
        log_dir: Directory for log file output.
        max_file_size_bytes: Maximum allowed upload file size in bytes.
        max_resumes_per_session: Maximum resumes a user can upload per session.
        api_host: FastAPI server bind host.
        api_port: FastAPI server bind port.
    """

    # --- Pydantic Settings Configuration ---
    # Reads from .env file in project root, environment variables take precedence.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore unknown env vars instead of raising errors
    )

    # --- Telegram ---
    telegram_bot_token: str = Field(
        ...,  # Required, no default — must be provided
        description="Telegram Bot API token from @BotFather",
    )

    # --- Gemini (Primary LLM Provider) ---
    gemini_api_key: str = Field(
        ...,
        description="Google Gemini API key (primary provider)",
    )
    gemini_model: str = Field(
        default="gemini-3.6-flash",
        description="Gemini model to use for extraction and evaluation",
    )
    gemini_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="LLM temperature. 0.0 = deterministic (PRD §12)",
    )
    gemini_max_tokens: int = Field(
        default=4096,
        gt=0,
        description="Maximum tokens per LLM response",
    )
    gemini_max_concurrent_requests: int = Field(
        default=2,
        gt=0,
        description="Maximum concurrent Gemini generation workflows.",
    )
    gemini_model_fallbacks: list[str] | str = Field(
        default_factory=lambda: [
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
        ],
        description="Ordered Gemini availability fallbacks for retryable API failures.",
    )

    # --- Deterministic Screening Weights ---
    score_weight_technical_skills: float = Field(default=40.0, ge=0.0)
    score_weight_projects: float = Field(default=20.0, ge=0.0)
    score_weight_experience: float = Field(default=20.0, ge=0.0)
    score_weight_education: float = Field(default=10.0, ge=0.0)
    score_weight_certifications: float = Field(default=10.0, ge=0.0)

    # --- OpenRouter (Fallback LLM Provider) ---
    # Design Decision: OpenRouter uses the OpenAI-compatible API format,
    # so we can reuse the openai SDK with a custom base_url. This means
    # zero additional dependencies for the fallback provider.
    openrouter_api_key: str = Field(
        default="",
        description="OpenRouter API key (fallback provider). Empty = fallback disabled.",
    )
    openrouter_model: str = Field(
        default="google/gemini-2.5-flash",
        description="Model to request via OpenRouter",
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter API base URL",
    )

    # --- Application ---
    log_level: str = Field(
        default="INFO",
        description="Python logging level",
    )
    upload_dir: str = Field(
        default="uploads",
        description="Temporary upload directory path",
    )
    log_dir: str = Field(
        default="logs",
        description="Log file output directory path",
    )
    max_file_size_bytes: int = Field(
        default=10_485_760,  # 10 MB
        gt=0,
        description="Maximum file upload size in bytes",
    )
    max_resumes_per_session: int = Field(
        default=20,
        gt=0,
        le=100,
        description="Maximum resumes per screening session",
    )

    # --- FastAPI ---
    api_host: str = Field(
        default="0.0.0.0",
        description="FastAPI server bind address",
    )
    api_port: int = Field(
        default=8000,
        gt=0,
        le=65535,
        description="FastAPI server bind port",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """
        Validate that the log level is a recognized Python logging level.

        Args:
            v: The log level string to validate.

        Returns:
            The uppercased, validated log level string.

        Raises:
            ValueError: If the log level is not recognized.
        """
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid_levels:
            raise ValueError(
                f"Invalid log level '{v}'. Must be one of: {', '.join(sorted(valid_levels))}"
            )
        return upper

    @field_validator("gemini_model_fallbacks", mode="before")
    @classmethod
    def parse_gemini_model_fallbacks(cls, value: str | list[str]) -> list[str]:
        """Allow an environment-friendly comma-separated fallback model list."""
        if isinstance(value, str):
            return [model.strip() for model in value.split(",") if model.strip()]
        return value

    @model_validator(mode="after")
    def validate_score_weights(self) -> "Settings":
        """Keep deterministic section weights on the documented 100-point scale."""
        total = (
            self.score_weight_technical_skills
            + self.score_weight_projects
            + self.score_weight_experience
            + self.score_weight_education
            + self.score_weight_certifications
        )
        if abs(total - 100.0) > 1e-9:
            raise ValueError("Score weights must total 100.")
        return self

    @property
    def fallback_enabled(self) -> bool:
        """
        Check whether the OpenRouter fallback provider is configured.

        Returns:
            True if an OpenRouter API key is provided, False otherwise.
        """
        return bool(self.openrouter_api_key)

    def ensure_directories(self) -> None:
        """
        Create required directories (uploads, logs) if they do not exist.

        Called during application startup to ensure the filesystem is ready.
        This avoids runtime errors when writing files or logs.
        """
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Singleton instance — import this throughout the application.
# Pydantic validates all values at import time, so misconfiguration
# is caught immediately rather than at first use.
# ---------------------------------------------------------------------------
settings = Settings()
