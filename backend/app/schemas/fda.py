"""Final Disbursement Account (FDA) Pydantic v2 schema — AI extraction output.

This is the structured output contract that Claude claude-sonnet-4-6 must satisfy.
It is injected into the LLM system prompt via model_json_schema() and validated
on every extraction response before the result is written to the database.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.pda import CategoryEnum  # re-use shared enum


class SupportingDocumentType(str, Enum):
    """Type of source document the AI found the cost item in."""

    DIGITAL_INVOICE = "DIGITAL_INVOICE"
    SCANNED_RECEIPT = "SCANNED_RECEIPT"
    HANDWRITTEN_CHIT = "HANDWRITTEN_CHIT"
    OFFICIAL_RECEIPT = "OFFICIAL_RECEIPT"


class BoundingBox(BaseModel):
    """PDF bounding-box coordinates output by Docling (in points, 1/72 inch).

    Origin is top-left of the page. The frontend converts points → CSS pixels
    using: px = (pt / 72) * rendered_dpi
    """

    model_config = ConfigDict(populate_by_name=True)

    page: int = Field(..., ge=1, description="1-based page number")
    x1: float = Field(..., ge=0.0, description="Left edge (points)")
    y1: float = Field(..., ge=0.0, description="Top edge (points)")
    x2: float = Field(..., ge=0.0, description="Right edge (points)")
    y2: float = Field(..., ge=0.0, description="Bottom edge (points)")

    @model_validator(mode='after')
    def ensure_ordered(self) -> 'BoundingBox':
        """LLMs sometimes return inverted coordinates — silently swap them."""
        if self.x2 < self.x1:
            self.x1, self.x2 = self.x2, self.x1
        if self.y2 < self.y1:
            self.y1, self.y2 = self.y2, self.y1
        return self


class ExtractedCostItem(BaseModel):
    """A single cost line item extracted by the AI from the FDA PDF."""

    model_config = ConfigDict(populate_by_name=True)

    category: CategoryEnum = Field(
        ...,
        description="Cost category — must match one of the PDA CategoryEnum values",
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Verbatim or normalised description from the source document",
    )
    actual_value: float = Field(
        ...,
        ge=0.0,
        description="Actual billed amount as extracted from the document",
    )
    currency: str = Field(
        ...,
        pattern=r"^[A-Z]{3}$",
        description="ISO 4217 currency code as found in the document",
    )
    confidence_score: float = Field(
        ...,
        description=(
            "AI confidence in this extraction [0.0–1.0]. "
            "Assign low scores for handwritten, ambiguous, or partially legible items."
        ),
    )
    pdf_citation_bounding_box: BoundingBox = Field(
        ...,
        description=(
            "Docling bounding-box coordinates for the source text/table cell. "
            "Used by the frontend to draw a highlight rectangle over the PDF."
        ),
    )
    supporting_document_type: SupportingDocumentType = Field(
        ...,
        description="Classification of the source document that contains this item",
    )

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"confidence_score must be between 0.0 and 1.0, got {v}")
        return round(v, 4)


class FDASchema(BaseModel):
    """Final Disbursement Account — complete AI extraction output document.

    This schema is serialised via model_json_schema() and injected verbatim
    into the Claude system prompt as the required output contract.
    """

    model_config = ConfigDict(populate_by_name=True)

    port_call_id: str = Field(
        ...,
        description="Must match the port_call_id from the corresponding PDA",
    )
    processing_job_id: str = Field(
        ...,
        description="Celery job ID for end-to-end traceability",
    )
    extraction_model: str = Field(
        default="claude-sonnet-4-6-20250514",
        description="Anthropic model identifier used for this extraction",
    )
    extracted_items: list[ExtractedCostItem] = Field(
        ...,
        description="All cost line items found in the FDA PDF",
    )
    items_not_found: list[CategoryEnum] = Field(
        default_factory=list,
        description=(
            "PDA cost categories for which no matching evidence was found in the FDA. "
            "These will be automatically flagged for accountant review."
        ),
    )
    total_actual: float = Field(
        ...,
        ge=0.0,
        description="Sum of all extracted actual_values (in the DA currency)",
    )
    extraction_notes: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional free-text notes from the AI about extraction difficulties",
    )
