"""Application settings — loaded from .env via pydantic-settings.

All LLM configuration is provider-agnostic. Set LLM_MODEL to any LiteLLM
model string (e.g. 'anthropic/claude-sonnet-4-6-20250514', 'openai/gpt-4o',
'gemini/gemini-2.0-flash', 'ollama/llama3.3') and LLM_API_KEY to the
corresponding API key. No code changes required when switching providers.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    upload_dir: str = Field(default="./uploads")

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://openda:openda@localhost:5432/openda",
        description="Async SQLAlchemy database URL",
    )

    # ── Redis / Celery ────────────────────────────────────────────────────────
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL used by Celery broker and result backend",
    )

    # ── LLM Provider (LiteLLM-routed — provider-agnostic) ────────────────────
    llm_model: str = Field(
        default="anthropic/claude-sonnet-4-6-20250514",
        description=(
            "LiteLLM model string. Examples:\n"
            "  anthropic/claude-sonnet-4-6-20250514\n"
            "  openai/gpt-4o\n"
            "  gemini/gemini-2.0-flash\n"
            "  ollama/llama3.3"
        ),
    )
    llm_api_key: str = Field(
        default="",
        description="API key for the configured LLM provider. Use 'ollama' for local Ollama.",
    )
    llm_max_tokens: int = Field(default=8192)
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    llm_timeout_seconds: int = Field(default=120)
    llm_max_retries: int = Field(default=3)

    # Ollama / Azure overrides (passed through to LiteLLM when set)
    ollama_api_base: str | None = Field(default=None)
    azure_api_base: str | None = Field(default=None)
    azure_api_version: str | None = Field(default=None)

    # ── Webhook ───────────────────────────────────────────────────────────────
    webhook_url: str = Field(
        default="http://localhost:8000/api/v1/da/webhook-echo",
        description="ERP/VMS webhook endpoint that receives the final canonical JSON",
    )

    # ── Auth (MVP: static user ids passed via X-User-Id header) ──────────────
    accountant_user_id: str = Field(default="accountant-001")
    operator_user_id: str = Field(default="operator-001")


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton — use as a FastAPI dependency."""
    return Settings()
