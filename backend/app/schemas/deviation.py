"""Deviation report Pydantic v2 schemas.

The DeviationEngine compares a PDA against an extracted FDA and produces
a DeviationReport that drives the accountant's review workflow and the
operator's approval dashboard.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.pda import CategoryEnum


class FlagReasonEnum(str, Enum):
    """Reason a cost item has been flagged for human review."""

    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    MISSING_PDA_LINE = "MISSING_PDA_LINE"
    HIGH_DEVIATION = "HIGH_DEVIATION"
    MISSING_FROM_FDA = "MISSING_FROM_FDA"


class ItemStatus(str, Enum):
    """Review status of a single deviation line."""

    OK = "OK"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    CONFIRMED = "CONFIRMED"   # accountant has explicitly confirmed the AI value
    OVERRIDDEN = "OVERRIDDEN"  # accountant has edited the AI value


class DeviationLineItem(BaseModel):
    """Per-line deviation result for a single cost category."""

    model_config = ConfigDict(populate_by_name=True)

    category: CategoryEnum = Field(..., description="Cost category being compared")
    pda_description: str | None = Field(
        default=None,
        description="Description from the PDA estimate (None if category not in PDA)",
    )
    fda_description: str | None = Field(
        default=None,
        description="Description from the FDA extraction (None if not found in FDA)",
    )
    estimated_value: float | None = Field(
        default=None,
        description="PDA estimated value (None if category not in PDA)",
    )
    actual_value: float | None = Field(
        default=None,
        description="FDA actual extracted value (None if not found in FDA)",
    )
    confidence_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="AI confidence score for the extracted item",
    )
    abs_variance: float | None = Field(
        default=None,
        description="Absolute variance: actual_value - estimated_value",
    )
    pct_variance: float | None = Field(
        default=None,
        description="Percentage variance relative to estimated_value",
    )
    status: ItemStatus = Field(
        default=ItemStatus.OK,
        description="Review status of this line item",
    )
    flag_reasons: list[FlagReasonEnum] = Field(
        default_factory=list,
        description="All reasons this item has been flagged (may be multiple)",
    )


class DeviationReport(BaseModel):
    """Complete deviation analysis between a PDA and an extracted FDA."""

    model_config = ConfigDict(populate_by_name=True)

    port_call_id: str = Field(..., description="Port call identifier")
    da_id: str = Field(..., description="DisbursementAccount database record ID")

    line_items: list[DeviationLineItem] = Field(
        ...,
        description="Per-category deviation breakdown",
    )

    # ── Aggregate statistics ──────────────────────────────────────────────────
    total_estimated: float = Field(
        ...,
        description="Total PDA estimate (sum of estimated_items)",
    )
    total_actual: float = Field(
        ...,
        description="Total FDA actual (sum of extracted_items)",
    )
    total_abs_variance: float = Field(
        ...,
        description="Absolute total variance: total_actual - total_estimated",
    )
    total_pct_variance: float | None = Field(
        default=None,
        description=(
            "Percentage total variance relative to total_estimated "
            "(None if estimated is zero)"
        ),
    )

    # ── Missing item lists ────────────────────────────────────────────────────
    items_not_billed: list[CategoryEnum] = Field(
        default_factory=list,
        description="PDA categories present in estimate but absent from FDA",
    )
    items_not_estimated: list[CategoryEnum] = Field(
        default_factory=list,
        description="FDA categories present in extraction but absent from PDA",
    )

    # ── Review summary ────────────────────────────────────────────────────────
    flagged_count: int = Field(
        default=0,
        description="Number of line items requiring human review",
    )
    review_complete: bool = Field(
        default=False,
        description="True only when all flagged items are CONFIRMED or OVERRIDDEN",
    )
