"""Health check endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Returns service health including DB and Redis connectivity."""
    settings = get_settings()
    status: dict[str, str | dict] = {
        "status": "ok",
        "app_env": settings.app_env,
        "llm_model": settings.llm_model,
        "llm_provider": settings.llm_model.split("/")[0]
        if "/" in settings.llm_model
        else settings.llm_model,
    }

    # ── DB check ──────────────────────────────────────────────────────────────
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        status["db"] = "connected"
    except Exception as exc:
        logger.warning("DB health check failed: %s", exc)
        status["db"] = f"error: {exc}"
        status["status"] = "degraded"

    # ── Redis check ───────────────────────────────────────────────────────────
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        status["redis"] = "connected"
    except Exception as exc:
        logger.warning("Redis health check failed: %s", exc)
        status["redis"] = f"error: {exc}"
        status["status"] = "degraded"

    return status
