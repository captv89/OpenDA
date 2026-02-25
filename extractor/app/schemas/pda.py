"""Proforma Disbursement Account (PDA) Pydantic v2 schemas.

The PDA is the port agent's upfront cost estimate sent to the ship operator
before the vessel arrives. It is the baseline against which the FDA is compared.
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CategoryEnum(str, Enum):
    """Cost categories shared across PDA and FDA schemas."""

    PILOTAGE = "PILOTAGE"
    TOWAGE = "TOWAGE"
    PORT_DUES = "PORT_DUES"
    AGENCY_FEE = "AGENCY_FEE"
    LAUNCH_HIRE = "LAUNCH_HIRE"
    WASTE_DISPOSAL = "WASTE_DISPOSAL"
    OTHER = "OTHER"


class UnitEnum(str, Enum):
    """Billing unit types."""

    PER_MOVEMENT = "per_movement"
    PER_HOUR = "per_hour"
    PER_DAY = "per_day"
    PER_TON = "per_ton"
    LUMP_SUM = "lump_sum"


class CostItem(BaseModel):
    """A single estimated cost line item in the PDA."""

    model_config = ConfigDict(populate_by_name=True)

    category: CategoryEnum
    description: str = Field(..., min_length=1, max_length=500)
    estimated_value: float = Field(..., ge=0.0)
    unit: UnitEnum
    quantity: float = Field(default=1.0, ge=0.0)


class PDASchema(BaseModel):
    """Proforma Disbursement Account — full document schema."""

    model_config = ConfigDict(populate_by_name=True)

    port_call_id: str = Field(..., pattern=r"^PC-\d{4}-[A-Z]{5}-\d{4}$")
    vessel_name: str = Field(..., min_length=1, max_length=200)
    vessel_imo: str = Field(..., pattern=r"^\d{7}$")
    port_code: str = Field(..., pattern=r"^[A-Z]{5}$")
    currency: str = Field(..., pattern=r"^[A-Z]{3}$")
    estimated_items: list[CostItem] = Field(..., min_length=1)
    total_estimated: float = Field(..., ge=0.0)
    valid_until: date
    prepared_by: str = Field(default="Port Agent")

    @model_validator(mode="after")
    def validate_total(self) -> "PDASchema":
        computed = round(
            sum(item.estimated_value * item.quantity for item in self.estimated_items), 2
        )
        declared = round(self.total_estimated, 2)
        if abs(computed - declared) > 0.01:
            raise ValueError(
                f"total_estimated ({declared}) does not match sum of estimated_items "
                f"({computed}). Difference: {abs(computed - declared):.2f}"
            )
        return self
