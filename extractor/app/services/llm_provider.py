"""LLM provider abstraction — powered by LiteLLM.

Switch providers by changing LLM_MODEL + LLM_API_KEY in .env.
Supported model strings (examples):
    anthropic/claude-sonnet-4-6-20250514   → Anthropic API
    openai/gpt-4o                          → OpenAI API
    gemini/gemini-2.0-flash                → Google AI API
    ollama/llama3.3                        → Local Ollama (no key needed)
    azure/gpt-4o                           → Azure OpenAI
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

import litellm

from app.config import Settings

logger = logging.getLogger(__name__)
litellm.suppress_debug_info = True


class LLMProviderError(Exception):
    """Raised when all LLM retries are exhausted or response is malformed."""


class AsyncLLMProvider:
    """Provider-agnostic async LLM client via LiteLLM."""

    def __init__(self, settings: Settings) -> None:
        self._model = settings.llm_model
        self._api_key = settings.llm_api_key
        self._max_tokens = settings.llm_max_tokens
        self._temperature = settings.llm_temperature
        self._timeout = settings.llm_timeout_seconds
        self._max_retries = settings.llm_max_retries

        if settings.llm_api_key:
            self._configure_api_key(settings)
        if settings.ollama_api_base:
            os.environ["OLLAMA_API_BASE"] = settings.ollama_api_base
        if settings.azure_api_base:
            os.environ["AZURE_API_BASE"] = settings.azure_api_base
        if settings.azure_api_version:
            os.environ["AZURE_API_VERSION"] = settings.azure_api_version

    def _configure_api_key(self, settings: Settings) -> None:
        model = settings.llm_model.lower()
        key = settings.llm_api_key
        if key in ("ollama", ""):
            return
        if model.startswith("anthropic/"):
            os.environ["ANTHROPIC_API_KEY"] = key
        elif model.startswith("openai/"):
            os.environ["OPENAI_API_KEY"] = key
        elif model.startswith("gemini/"):
            os.environ["GEMINI_API_KEY"] = key
        elif model.startswith("azure/"):
            os.environ["AZURE_API_KEY"] = key
        else:
            os.environ["OPENAI_API_KEY"] = key

    @property
    def provider_name(self) -> str:
        return self._model.split("/")[0] if "/" in self._model else self._model

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        *,
        expect_json: bool = True,
    ) -> str:
        if expect_json:
            system_prompt = (
                system_prompt
                + "\n\nCRITICAL: Your response MUST be valid JSON only — "
                "no markdown fences, no explanatory text, no trailing commas."
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                logger.info("LLM call attempt %d/%d model=%s", attempt, self._max_retries, self._model)
                response = await litellm.acompletion(
                    model=self._model,
                    messages=messages,
                    max_tokens=self._max_tokens,
                    temperature=self._temperature,
                    timeout=self._timeout,
                )
                content: str = response.choices[0].message.content or ""

                if expect_json and content:
                    content = _strip_json_fence(content)
                    try:
                        json.loads(content)
                    except json.JSONDecodeError:
                        logger.warning("LLM response is not valid JSON (attempt %d): %s…", attempt, content[:200])

                logger.info("LLM call succeeded model=%s tokens=%s", self._model, getattr(response.usage, "total_tokens", "?"))
                return content

            except litellm.exceptions.RateLimitError as exc:
                wait = 2**attempt
                logger.warning("Rate limit on attempt %d — retrying in %ds", attempt, wait)
                last_error = exc
                await asyncio.sleep(wait)
            except litellm.exceptions.APIConnectionError as exc:
                wait = 2**attempt
                logger.warning("Connection error on attempt %d — retrying in %ds", attempt, wait)
                last_error = exc
                await asyncio.sleep(wait)
            except litellm.exceptions.AuthenticationError as exc:
                raise LLMProviderError(
                    f"Authentication failed for model '{self._model}'. Check LLM_API_KEY."
                ) from exc
            except Exception as exc:
                wait = 2**attempt
                logger.warning("LLM error on attempt %d (%s) — retrying in %ds", attempt, exc, wait)
                last_error = exc
                await asyncio.sleep(wait)

        raise LLMProviderError(
            f"LLM call failed after {self._max_retries} attempts for '{self._model}': {last_error}"
        ) from last_error


def _strip_json_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(inner).strip()
    return text
