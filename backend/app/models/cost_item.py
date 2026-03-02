"""CostItem SQLAlchemy model — one row per extracted line item."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.disbursement_account import DisbursementAccount

CATEGORY_VALUES = [
    "PILOTAGE",
    "TOWAGE",
    "PORT_DUES",
    "AGENCY_FEE",
    "LAUNCH_HIRE",
    "WASTE_DISPOSAL",
    "OTHER",
]

FLAG_REASON_VALUES = [
    "LOW_CONFIDENCE",
    "MISSING_PDA_LINE",
    "HIGH_DEVIATION",
    "MISSING_FROM_FDA",
]

ITEM_STATUS_VALUES = ["OK", "REQUIRES_REVIEW", "CONFIRMED", "OVERRIDDEN"]

DOC_TYPE_VALUES = [
    "DIGITAL_INVOICE",
    "SCANNED_RECEIPT",
    "HANDWRITTEN_CHIT",
    "OFFICIAL_RECEIPT",
]


class CostItem(Base):
    __tablename__ = "cost_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    da_fk: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("disbursement_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Source (PDA / FDA / both)
    source: Mapped[str] = mapped_column(
        SAEnum("PDA", "FDA", name="cost_item_source_enum"), nullable=False
    )

    # Classification
    category: Mapped[str] = mapped_column(
        SAEnum(*CATEGORY_VALUES, name="category_enum"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Values
    estimated_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    # AI extraction metadata
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    supporting_document_type: Mapped[str | None] = mapped_column(
        SAEnum(*DOC_TYPE_VALUES, name="doc_type_enum"), nullable=True
    )
    # Docling bounding box stored as JSONB {page, x1, y1, x2, y2}
    bounding_box: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Deviation
    abs_variance: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct_variance: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Review workflow
    review_status: Mapped[str] = mapped_column(
        SAEnum(*ITEM_STATUS_VALUES, name="item_status_enum"),
        nullable=False,
        default="OK",
        index=True,
    )
    flag_reason: Mapped[str | None] = mapped_column(
        SAEnum(*FLAG_REASON_VALUES, name="flag_reason_enum"), nullable=True
    )
    # Stores multiple flag reasons as JSON array when needed
    flag_reasons: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Accountant override / confirmation
    accountant_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    operator_justification: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    # Relationships
    disbursement_account: Mapped[DisbursementAccount] = relationship(
        "DisbursementAccount", back_populates="cost_items"
    )

    def __repr__(self) -> str:
        return f"<CostItem {self.category} {self.review_status}>"
