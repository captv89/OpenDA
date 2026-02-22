"""OpenDA FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import da, health
from app.config import get_settings
from app.database import engine
from app.models.base import Base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: create tables (dev only). Shutdown: dispose DB engine."""
    logger.info("OpenDA starting — env=%s  llm=%s", settings.app_env, settings.llm_model)

    if settings.app_env == "development":
        # Auto-create tables in dev (production uses Alembic migrations)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ensured (development mode)")

    yield  # ← application runs here

    await engine.dispose()
    logger.info("OpenDA shutdown — DB connection pool disposed")


app = FastAPI(
    title="OpenDA API",
    description=(
        "AI Disbursement Account Analyzer — provider-agnostic LLM extraction "
        "(Claude, Gemini, OpenAI, Ollama) via LiteLLM"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS (wide open for local dev — tighten in production) ───────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router, prefix="/api/v1")
app.include_router(da.router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {
        "service": "OpenDA API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "llm_provider": settings.llm_model.split("/")[0] if "/" in settings.llm_model else settings.llm_model,
        "llm_model": settings.llm_model,
    }
