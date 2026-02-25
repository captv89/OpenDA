"""OpenDA Extractor — settings (LLM only; no DB or Redis)."""

from __future__ import annotations

import os
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

    log_level: str = Field(default="INFO")

    # ── LLM Provider (LiteLLM-routed — provider-agnostic) ────────────────────
    llm_model: str = Field(
        default="anthropic/claude-sonnet-4-6-20250514",
        description="LiteLLM model string",
    )
    llm_api_key: str = Field(default="")
    llm_max_tokens: int = Field(default=8192)
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    llm_timeout_seconds: int = Field(default=120)
    llm_max_retries: int = Field(default=3)

    ollama_api_base: str | None = Field(default=None)
    azure_api_base: str | None = Field(default=None)
    azure_api_version: str | None = Field(default=None)


@lru_cache
def get_settings() -> Settings:
    return Settings()
