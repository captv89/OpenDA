"""Application settings — loaded from .env via pydantic-settings."""

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
    )

    # ── Redis / Celery ────────────────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0")

    # ── Extractor microservice ─────────────────────────────────────────────────
    # Heavy extraction work (Docling + LLM) is delegated here via HTTP.
    # Override to http://localhost:8001 for local dev without Docker.
    extractor_url: str = Field(default="http://extractor:8001")

    # ── LLM model (audit logging only — actual calls are made by extractor) ───
    llm_model: str = Field(default="anthropic/claude-sonnet-4-6-20250514")

    # ── Webhook ───────────────────────────────────────────────────────────────
    webhook_url: str = Field(
        default="http://localhost:8000/api/v1/da/webhook-echo",
    )

    # ── Auth (MVP: static user ids passed via X-User-Id header) ──────────────
    accountant_user_id: str = Field(default="accountant-001")
    operator_user_id: str = Field(default="operator-001")


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton — use as a FastAPI dependency."""
    return Settings()
