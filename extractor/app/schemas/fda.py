"""Final Disbursement Account (FDA) Pydantic v2 schema — AI extraction output."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.pda import CategoryEnum


class SupportingDocumentType(str, Enum):
    DIGITAL_INVOICE = "DIGITAL_INVOICE"
    SCANNED_RECEIPT = "SCANNED_RECEIPT"
    HANDWRITTEN_CHIT = "HANDWRITTEN_CHIT"
    OFFICIAL_RECEIPT = "OFFICIAL_RECEIPT"


class BoundingBox(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    page: int = Field(..., ge=1)
    x1: float = Field(..., ge=0.0)
    y1: float = Field(..., ge=0.0)
    x2: float = Field(..., ge=0.0)
    y2: float = Field(..., ge=0.0)

    @model_validator(mode='after')
    def ensure_ordered(self) -> 'BoundingBox':
        """LLMs sometimes return inverted coordinates — silently swap them."""
        if self.x2 < self.x1:
            self.x1, self.x2 = self.x2, self.x1
        if self.y2 < self.y1:
            self.y1, self.y2 = self.y2, self.y1
        return self


class ExtractedCostItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    category: CategoryEnum
    description: str = Field(..., min_length=1, max_length=500)
    actual_value: float = Field(..., ge=0.0)
    currency: str = Field(..., pattern=r"^[A-Z]{3}$")
    confidence_score: float
    pdf_citation_bounding_box: BoundingBox
    supporting_document_type: SupportingDocumentType

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"confidence_score must be between 0.0 and 1.0, got {v}")
        return round(v, 4)


class FDASchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    port_call_id: str
    processing_job_id: str
    extraction_model: str = Field(default="claude-sonnet-4-6-20250514")
    extracted_items: list[ExtractedCostItem]
    items_not_found: list[CategoryEnum] = Field(default_factory=list)
    total_actual: float = Field(..., ge=0.0)
    extraction_notes: str | None = Field(default=None, max_length=2000)
