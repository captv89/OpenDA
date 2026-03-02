"""DisbursementAccount SQLAlchemy model with state machine enum."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.audit_log import AuditLog
    from app.models.cost_item import CostItem
    from app.models.port_call import PortCall


class DAStatus(str):
    """DA lifecycle states — used as Python-level enum values in the SA column."""

    UPLOADING = "UPLOADING"
    AI_PROCESSING = "AI_PROCESSING"
    PENDING_ACCOUNTANT_REVIEW = "PENDING_ACCOUNTANT_REVIEW"
    PENDING_OPERATOR_APPROVAL = "PENDING_OPERATOR_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PUSHED_TO_ERP = "PUSHED_TO_ERP"


DA_STATUS_VALUES = [
    "UPLOADING",
    "AI_PROCESSING",
    "PENDING_ACCOUNTANT_REVIEW",
    "PENDING_OPERATOR_APPROVAL",
    "APPROVED",
    "REJECTED",
    "PUSHED_TO_ERP",
]


class DisbursementAccount(Base):
    __tablename__ = "disbursement_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    port_call_fk: Mapped[str] = mapped_column(
        String(36), ForeignKey("port_calls.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        SAEnum(*DA_STATUS_VALUES, name="da_status_enum"),
        nullable=False,
        default="UPLOADING",
        index=True,
    )

    # Storage
    pdf_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    celery_job_id: Mapped[str | None] = mapped_column(String(155), nullable=True, index=True)

    # AI extraction model used (e.g. 'anthropic/claude-sonnet-4-6-20250514')
    extraction_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    llm_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Stored JSON payloads (JSONB for indexing + querying)
    pda_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    fda_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    deviation_report: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Accountant + operator metadata
    accountant_user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    operator_user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    operator_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Counts updated after flagging
    flagged_items_count: Mapped[int] = mapped_column(default=0)
    total_estimated: Mapped[float | None] = mapped_column(nullable=True)
    total_actual: Mapped[float | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    # Relationships
    port_call: Mapped[PortCall] = relationship("PortCall", back_populates="disbursement_accounts")
    cost_items: Mapped[list[CostItem]] = relationship(
        "CostItem", back_populates="disbursement_account", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(
        "AuditLog", back_populates="disbursement_account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<DisbursementAccount {self.id} [{self.status}]>"
