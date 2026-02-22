"""Celery task definitions for background FDA processing.

Tasks are synchronous entry points that delegate to async services via
asyncio.run(). Each Celery worker process has its own event loop, so
this pattern is safe and avoids the complexity of async Celery configuration.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models.disbursement_account import DisbursementAccount
from app.schemas.pda import PDASchema
from app.services.deviation_engine import DeviationEngine
from app.services.extraction_service import ExtractionService
from app.services.state_machine import DAStateMachine
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _get_session(database_url: str) -> tuple[AsyncSession, object]:
    """Create a fresh engine + session for use inside a Celery worker."""
    engine = create_async_engine(database_url, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    session = AsyncSessionLocal()
    return session, engine


async def _async_process_fda(
    da_id: str,
    pdf_path: str,
    port_call_id: str,
    job_id: str,
) -> dict:
    """Async implementation of the FDA processing pipeline."""
    settings = get_settings()
    session, engine = await _get_session(settings.database_url)

    try:
        from sqlalchemy import select

        # ── Load the DA record ────────────────────────────────────────────────
        result = await session.execute(
            select(DisbursementAccount).where(DisbursementAccount.id == da_id)
        )
        da = result.scalar_one_or_none()
        if da is None:
            raise ValueError(f"DisbursementAccount {da_id} not found")

        state_machine = DAStateMachine()
        extraction_service = ExtractionService(settings)
        deviation_engine = DeviationEngine()

        # ── Transition: UPLOADING → AI_PROCESSING ────────────────────────────
        await state_machine.transition(
            da, "AI_PROCESSING", "SYSTEM", session,
            note="Celery task started",
            llm_provider=settings.llm_model,
        )
        da.celery_job_id = job_id
        await session.commit()

        # ── Load PDA JSON from DB ─────────────────────────────────────────────
        if da.pda_json is None:
            raise ValueError(f"DA {da_id} has no pda_json stored")
        pda = PDASchema.model_validate(da.pda_json)

        # ── Run extraction ────────────────────────────────────────────────────
        fda = await extraction_service.process_pdf(pdf_path, pda, job_id)
        da.fda_json = json.loads(fda.model_dump_json())
        da.extraction_model = fda.extraction_model
        da.llm_provider = extraction_service._llm.provider_name
        da.total_actual = fda.total_actual

        # ── Run deviation analysis ────────────────────────────────────────────
        report = deviation_engine.compare(pda, fda, da_id)
        da.deviation_report = json.loads(report.model_dump_json())
        da.flagged_items_count = report.flagged_count

        # ── Transition: AI_PROCESSING → PENDING_ACCOUNTANT_REVIEW ────────────
        await state_machine.transition(
            da, "PENDING_ACCOUNTANT_REVIEW", "SYSTEM", session,
            note=f"Extraction complete — {report.flagged_count} items flagged",
            llm_provider=settings.llm_model,
        )
        await session.commit()

        return {
            "da_id": da_id,
            "status": "PENDING_ACCOUNTANT_REVIEW",
            "flagged_count": report.flagged_count,
            "total_actual": fda.total_actual,
            "llm_provider": extraction_service._llm.provider_name,
        }

    except Exception as exc:
        logger.error("FDA processing failed for DA %s: %s", da_id, exc, exc_info=True)
        # Attempt to persist error state
        try:
            from sqlalchemy import select as sel2
            result2 = await session.execute(
                sel2(DisbursementAccount).where(DisbursementAccount.id == da_id)
            )
            da2 = result2.scalar_one_or_none()
            if da2:
                da2.status = "UPLOADING"  # allow retry
                await session.commit()
        except Exception:
            pass
        raise

    finally:
        await session.close()
        await engine.dispose()


@celery_app.task(
    bind=True,
    name="app.workers.tasks.process_fda_document",
    max_retries=3,
    default_retry_delay=30,
)
def process_fda_document(
    self: Task,
    da_id: str,
    pdf_path: str,
    port_call_id: str,
) -> dict:
    """Celery task: run full FDA extraction + deviation pipeline.

    Args:
        da_id: UUID of the DisbursementAccount DB record.
        pdf_path: Absolute path to the uploaded PDF file.
        port_call_id: Port call identifier (for logging).

    Returns:
        Dict with final status, flagged_count, and total_actual.
    """
    try:
        return asyncio.run(
            _async_process_fda(da_id, pdf_path, port_call_id, self.request.id or da_id)
        )
    except Exception as exc:
        logger.error("Task %s failed: %s", self.request.id, exc)
        raise self.retry(exc=exc) from exc
