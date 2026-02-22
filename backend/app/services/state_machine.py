"""DA state machine — validates transitions and writes to audit_log."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.disbursement_account import DA_STATUS_VALUES

if TYPE_CHECKING:
    from app.models.disbursement_account import DisbursementAccount

logger = logging.getLogger(__name__)

# ── Valid state transitions ───────────────────────────────────────────────────
VALID_TRANSITIONS: dict[str, list[str]] = {
    "UPLOADING": ["AI_PROCESSING"],
    "AI_PROCESSING": ["PENDING_ACCOUNTANT_REVIEW", "UPLOADING"],  # retry → UPLOADING
    "PENDING_ACCOUNTANT_REVIEW": ["PENDING_OPERATOR_APPROVAL", "REJECTED"],
    "PENDING_OPERATOR_APPROVAL": ["APPROVED", "REJECTED", "PENDING_ACCOUNTANT_REVIEW"],
    "APPROVED": ["PUSHED_TO_ERP"],
    "REJECTED": [],          # terminal
    "PUSHED_TO_ERP": [],     # terminal
}


class InvalidTransitionError(Exception):
    """Raised when a state transition is not permitted."""


class DAStateMachine:
    """Validates and executes DA state transitions, writing an audit log entry."""

    async def transition(
        self,
        da: "DisbursementAccount",
        new_status: str,
        actor: str,
        session: AsyncSession,
        *,
        note: str | None = None,
        llm_provider: str | None = None,
    ) -> None:
        """Attempt a state transition for the given DA.

        Args:
            da: The DisbursementAccount ORM instance (will be mutated in-place).
            new_status: The target status string.
            actor: User ID or 'SYSTEM' for automated transitions.
            session: Active async SQLAlchemy session.
            note: Optional free-text reason for the transition.
            llm_provider: LLM provider identifier (recorded for AI transitions).

        Raises:
            InvalidTransitionError: If the transition is not allowed.
        """
        current = da.status
        allowed = VALID_TRANSITIONS.get(current, [])

        if new_status not in allowed:
            raise InvalidTransitionError(
                f"Cannot transition DA {da.id} from '{current}' to '{new_status}'. "
                f"Allowed targets: {allowed}"
            )

        logger.info(
            "DA %s: %s → %s (actor=%s)",
            da.id,
            current,
            new_status,
            actor,
        )

        da.status = new_status

        audit = AuditLog(
            da_fk=da.id,
            actor=actor,
            previous_status=current,
            new_status=new_status,
            note=note,
            llm_provider=llm_provider,
        )
        session.add(audit)
        # Caller is responsible for committing the session.
