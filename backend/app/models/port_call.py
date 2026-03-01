"""PortCall SQLAlchemy model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow


class PortCall(Base):
    __tablename__ = "port_calls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    port_call_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    vessel_name: Mapped[str] = mapped_column(String(200), nullable=False)
    vessel_imo: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    port_code: Mapped[str] = mapped_column(String(5), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    # Relationships
    disbursement_accounts: Mapped[list[DisbursementAccount]] = relationship(
        "DisbursementAccount", back_populates="port_call", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PortCall {self.port_call_id} {self.vessel_name}>"
