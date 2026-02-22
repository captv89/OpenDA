"""Disbursement Account API routes."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.disbursement_account import DisbursementAccount
from app.models.port_call import PortCall
from app.schemas.deviation import DeviationReport
from app.schemas.fda import FDASchema
from app.schemas.pda import PDASchema
from app.services.state_machine import DAStateMachine, InvalidTransitionError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/da", tags=["Disbursement Account"])

_state_machine = DAStateMachine()


# ── Response models ───────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    job_id: str
    da_id: str
    status: str
    message: str


class DAStatusResponse(BaseModel):
    da_id: str
    port_call_id: str
    status: str
    flagged_items_count: int
    total_estimated: float | None
    total_actual: float | None
    extraction_model: str | None
    llm_provider: str | None
    created_at: str
    updated_at: str


class SubmitToOperatorRequest(BaseModel):
    corrected_items: list[dict]  # updated ExtractedCostItem list from accountant


class ApproveRequest(BaseModel):
    operator_remarks: str
    item_justifications: dict[str, str]  # category → justification comment


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_da_or_404(da_id: str, session: AsyncSession) -> DisbursementAccount:
    result = await session.execute(
        select(DisbursementAccount).where(DisbursementAccount.id == da_id)
    )
    da = result.scalar_one_or_none()
    if da is None:
        raise HTTPException(status_code=404, detail=f"DisbursementAccount {da_id} not found")
    return da


def _get_user_id(x_user_id: str | None, settings: Settings, role: str) -> str:
    """Extract user ID from header, fall back to MVP hardcoded identity."""
    if x_user_id:
        return x_user_id
    if role == "accountant":
        return settings.accountant_user_id
    return settings.operator_user_id


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_fda(
    port_call_id: str = Form(..., description="Port call identifier e.g. PC-2025-SGSIN-0042"),
    pda_json: str = Form(..., description="PDA JSON string (serialised PDASchema)"),
    fda_pdf: UploadFile = File(..., description="FDA PDF file"),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UploadResponse:
    """Upload an FDA PDF and enqueue it for AI extraction.

    Returns immediately with a job_id. Poll GET /da/{da_id}/status for progress.
    """
    # ── Validate file type ────────────────────────────────────────────────────
    if fda_pdf.content_type not in ("application/pdf", "application/octet-stream"):
        filename = fda_pdf.filename or ""
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400, detail="Only PDF files are accepted"
            )

    # ── Validate PDA JSON ─────────────────────────────────────────────────────
    try:
        pda = PDASchema.model_validate_json(pda_json)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid PDA JSON: {exc}") from exc

    if pda.port_call_id != port_call_id:
        raise HTTPException(
            status_code=422,
            detail=f"port_call_id mismatch: form={port_call_id}, pda={pda.port_call_id}",
        )

    # ── Upsert PortCall ───────────────────────────────────────────────────────
    result = await session.execute(
        select(PortCall).where(PortCall.port_call_id == port_call_id)
    )
    port_call = result.scalar_one_or_none()
    if port_call is None:
        port_call = PortCall(
            port_call_id=port_call_id,
            vessel_name=pda.vessel_name,
            vessel_imo=pda.vessel_imo,
            port_code=pda.port_code,
            currency=pda.currency,
        )
        session.add(port_call)
        await session.flush()

    # ── Save PDF to disk ──────────────────────────────────────────────────────
    upload_dir = Path(settings.upload_dir) / port_call_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_id = str(uuid.uuid4())
    pdf_path = upload_dir / f"{file_id}.pdf"
    content = await fda_pdf.read()
    pdf_path.write_bytes(content)

    # ── Create DA record ──────────────────────────────────────────────────────
    da_id = str(uuid.uuid4())
    da = DisbursementAccount(
        id=da_id,
        port_call_fk=port_call.id,
        status="UPLOADING",
        pdf_path=str(pdf_path),
        pda_json=json.loads(pda.model_dump_json()),
        total_estimated=pda.total_estimated,
    )
    session.add(da)
    await session.commit()

    # ── Enqueue Celery task ───────────────────────────────────────────────────
    from app.workers.tasks import process_fda_document  # avoid circular import

    task = process_fda_document.delay(da_id, str(pdf_path), port_call_id)
    da.celery_job_id = task.id
    await session.commit()

    logger.info(
        "Uploaded FDA for port_call=%s da_id=%s job=%s pdf=%s",
        port_call_id, da_id, task.id, pdf_path.name,
    )

    return UploadResponse(
        job_id=task.id,
        da_id=da_id,
        status="UPLOADING",
        message="PDF accepted, AI extraction queued.",
    )


@router.get("/{da_id}/status", response_model=DAStatusResponse)
async def get_da_status(
    da_id: str,
    session: AsyncSession = Depends(get_db),
) -> DAStatusResponse:
    """Return current DA status, flagged item count, and timestamps."""
    da = await _get_da_or_404(da_id, session)

    result = await session.execute(
        select(PortCall).where(PortCall.id == da.port_call_fk)
    )
    port_call = result.scalar_one()

    return DAStatusResponse(
        da_id=da.id,
        port_call_id=port_call.port_call_id,
        status=da.status,
        flagged_items_count=da.flagged_items_count,
        total_estimated=da.total_estimated,
        total_actual=da.total_actual,
        extraction_model=da.extraction_model,
        llm_provider=da.llm_provider,
        created_at=da.created_at.isoformat(),
        updated_at=da.updated_at.isoformat(),
    )


@router.get("/{da_id}/deviation-report")
async def get_deviation_report(
    da_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Return the full deviation report JSON for a DA."""
    da = await _get_da_or_404(da_id, session)
    if da.deviation_report is None:
        raise HTTPException(status_code=404, detail="Deviation report not yet available")
    return da.deviation_report


@router.put("/{da_id}/submit-to-operator", status_code=status.HTTP_200_OK)
async def submit_to_operator(
    da_id: str,
    body: SubmitToOperatorRequest,
    x_user_id: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Accountant submits reviewed + corrected FDA to the operator."""
    da = await _get_da_or_404(da_id, session)
    user_id = _get_user_id(x_user_id, settings, "accountant")

    if da.status != "PENDING_ACCOUNTANT_REVIEW":
        raise HTTPException(
            status_code=409,
            detail=f"DA must be in PENDING_ACCOUNTANT_REVIEW state (current: {da.status})",
        )

    # Update the stored FDA JSON with accountant corrections
    if da.fda_json and body.corrected_items:
        da.fda_json = {**da.fda_json, "extracted_items": body.corrected_items}

    da.accountant_user_id = user_id

    try:
        await _state_machine.transition(
            da, "PENDING_OPERATOR_APPROVAL", user_id, session,
            note="Accountant review complete, submitted to operator",
        )
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    await session.commit()
    return {"da_id": da_id, "status": da.status, "submitted_by": user_id}


@router.post("/{da_id}/approve", status_code=status.HTTP_200_OK)
async def approve_da(
    da_id: str,
    body: ApproveRequest,
    x_user_id: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Operator approves the DA, fires the webhook, transitions to APPROVED."""
    da = await _get_da_or_404(da_id, session)
    user_id = _get_user_id(x_user_id, settings, "operator")

    if da.status != "PENDING_OPERATOR_APPROVAL":
        raise HTTPException(
            status_code=409,
            detail=f"DA must be in PENDING_OPERATOR_APPROVAL state (current: {da.status})",
        )

    da.operator_user_id = user_id
    da.operator_remarks = body.operator_remarks

    try:
        await _state_machine.transition(
            da, "APPROVED", user_id, session,
            note=f"Operator approved: {body.operator_remarks[:100]}",
        )
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    await session.commit()

    # ── Build canonical webhook payload ───────────────────────────────────────
    payload = {
        "da_id": da_id,
        "status": "APPROVED",
        "port_call": da.pda_json,
        "fda": da.fda_json,
        "deviation_report": da.deviation_report,
        "approval": {
            "operator_user_id": user_id,
            "operator_remarks": body.operator_remarks,
            "item_justifications": body.item_justifications,
        },
        "llm_provider": da.llm_provider,
        "extraction_model": da.extraction_model,
    }

    # ── Fire webhook ──────────────────────────────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(settings.webhook_url, json=payload)
            resp.raise_for_status()
            logger.info("Webhook fired to %s → HTTP %d", settings.webhook_url, resp.status_code)

        # Transition to PUSHED_TO_ERP
        await _state_machine.transition(
            da, "PUSHED_TO_ERP", "SYSTEM", session,
            note=f"Webhook delivered to {settings.webhook_url}",
        )
        await session.commit()
    except Exception as exc:
        logger.error("Webhook delivery failed: %s", exc)
        # Don't roll back approval — log and let operator retry

    return {"da_id": da_id, "status": da.status, "webhook_url": settings.webhook_url}


@router.post("/{da_id}/reject", status_code=status.HTTP_200_OK)
async def reject_da(
    da_id: str,
    reason: str = Form(default="Rejected by reviewer"),
    x_user_id: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Reject a DA at any review stage."""
    da = await _get_da_or_404(da_id, session)
    user_id = _get_user_id(x_user_id, settings, "accountant")

    try:
        await _state_machine.transition(
            da, "REJECTED", user_id, session, note=reason
        )
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    await session.commit()
    return {"da_id": da_id, "status": "REJECTED", "reason": reason}


@router.get("/{da_id}/audit-log", status_code=status.HTTP_200_OK)
async def get_audit_log(
    da_id: str,
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return the full ordered audit trail for a DA."""
    # Verify DA exists
    await _get_da_or_404(da_id, session)

    result = await session.execute(
        select(AuditLog)
        .where(AuditLog.da_fk == da_id)
        .order_by(AuditLog.created_at)
    )
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "actor": log.actor,
            "previous_status": log.previous_status,
            "new_status": log.new_status,
            "note": log.note,
            "llm_provider": log.llm_provider,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]


@router.post("/webhook-echo", include_in_schema=True, tags=["Dev"])
async def webhook_echo(payload: dict) -> dict:
    """Debug endpoint: receives and echoes the final canonical approval payload.

    Replace WEBHOOK_URL in .env with your ERP/VMS endpoint in production.
    """
    logger.info("Webhook echo received — DA: %s, status: %s", payload.get("da_id"), payload.get("status"))
    return {"received": True, "da_id": payload.get("da_id"), "status": payload.get("status")}
