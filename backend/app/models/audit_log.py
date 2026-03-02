"""AuditLog SQLAlchemy model — immutable record of every DA state transition."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.disbursement_account import DisbursementAccount


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    da_fk: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("disbursement_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    actor: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="User ID or 'SYSTEM' for automated transitions",
    )
    previous_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # LLM provider recorded for AI transitions (traceability across model changes)
    llm_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    # Relationships
    disbursement_account: Mapped[DisbursementAccount] = relationship(
        "DisbursementAccount", back_populates="audit_logs"
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.previous_status} → {self.new_status} by {self.actor}>"
