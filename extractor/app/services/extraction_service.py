"""Docling + LLM extraction service (runs inside the extractor container)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from docling.document_converter import DocumentConverter

from app.config import Settings
from app.schemas.fda import FDASchema
from app.schemas.pda import PDASchema
from app.services.llm_provider import AsyncLLMProvider, LLMProviderError

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT_TEMPLATE = """\
You are an expert maritime disbursement account auditor. Your task is to extract
all cost line items from the provided Final Disbursement Account (FDA) document
text and return them as a single JSON object that exactly matches the schema below.

=== REQUIRED OUTPUT SCHEMA ===
{fda_schema}

=== EXTRACTION RULES ===
1. Extract EVERY cost line item you find. Do not skip items even if they appear duplicated.
2. For each item, assign a confidence_score [0.0–1.0]:
   - 0.95–1.0: Clearly printed digital invoice text, unambiguous amount
   - 0.80–0.94: Clean scanned receipt, amounts clearly legible
   - 0.60–0.79: Slightly unclear scan, handwritten chit, or partially legible amount
   - 0.40–0.59: Very unclear, rotated, or ambiguous text
   - <0.40: Almost certainly incorrect or estimated
3. For pdf_citation_bounding_box, use the Docling bounding box coordinates.
4. Classify supporting_document_type based on document description.
5. Map each item to the nearest CategoryEnum value:
   PILOTAGE | TOWAGE | PORT_DUES | AGENCY_FEE | LAUNCH_HIRE | WASTE_DISPOSAL | OTHER
6. List any PDA categories not found in the FDA in items_not_found.
7. Set total_actual to the sum of all actual_value fields.
8. The port_call_id must match exactly: {port_call_id}
9. The processing_job_id must be: {job_id}
10. The extraction_model must be: {extraction_model}

RETURN ONLY VALID JSON — no markdown fences, no explanatory text.
"""


class ExtractionService:
    """Two-step FDA extraction: Docling PDF parsing → LLM structured extraction."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._llm = AsyncLLMProvider(settings)
        self._converter = DocumentConverter()

    async def process_pdf(self, pdf_path: str | Path, pda: PDASchema, job_id: str) -> FDASchema:
        pdf_path = Path(pdf_path)
        logger.info("Starting extraction for %s (job=%s)", pdf_path.name, job_id)

        docling_output = self._parse_pdf(pdf_path)
        logger.info("Docling parsed %d pages, %d blocks", docling_output["page_count"], docling_output["block_count"])

        fda_schema_str = json.dumps(FDASchema.model_json_schema(), indent=2)
        pda_categories = [item.category.value for item in pda.estimated_items]

        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
            fda_schema=fda_schema_str,
            port_call_id=pda.port_call_id,
            job_id=job_id,
            extraction_model=self._settings.llm_model,
        )
        user_message = self._build_user_message(docling_output, pda, pda_categories)

        raw_json = await self._llm.complete(system_prompt, user_message, expect_json=True)

        try:
            fda = FDASchema.model_validate_json(raw_json)
        except Exception as exc:
            logger.error("FDA schema validation failed: %s\nRaw: %s…", exc, raw_json[:500])
            raise LLMProviderError(f"LLM returned invalid FDA JSON: {exc}") from exc

        logger.info("Extraction complete: %d items, total=%.2f, provider=%s",
                    len(fda.extracted_items), fda.total_actual, self._llm.provider_name)
        return fda

    def _parse_pdf(self, pdf_path: Path) -> dict:
        result = self._converter.convert(str(pdf_path))
        doc = result.document
        doc_dict = doc.export_to_dict()

        text_blocks: list[dict] = []
        page_count = 0
        for page_no, page in enumerate(doc.pages, start=1):
            page_count = max(page_count, page_no)

        for item in doc_dict.get("texts", []):
            prov = item.get("prov", [{}])[0] if item.get("prov") else {}
            bbox = prov.get("bbox", {})
            text_blocks.append({
                "text": item.get("text", ""),
                "label": item.get("label", "text"),
                "page": prov.get("page_no", 1),
                "bbox": {
                    "x1": bbox.get("l", 0.0), "y1": bbox.get("t", 0.0),
                    "x2": bbox.get("r", 0.0), "y2": bbox.get("b", 0.0),
                },
            })

        tables: list[dict] = []
        for table in doc_dict.get("tables", []):
            prov = table.get("prov", [{}])[0] if table.get("prov") else {}
            bbox = prov.get("bbox", {})
            cells = []
            for row in table.get("data", {}).get("grid", []):
                for cell in row:
                    if cell and cell.get("text"):
                        cells.append(cell["text"])
            tables.append({
                "page": prov.get("page_no", 1),
                "cells": cells,
                "bbox": {
                    "x1": bbox.get("l", 0.0), "y1": bbox.get("t", 0.0),
                    "x2": bbox.get("r", 0.0), "y2": bbox.get("b", 0.0),
                },
            })

        return {
            "page_count": page_count or 1,
            "block_count": len(text_blocks),
            "text_blocks": text_blocks,
            "tables": tables,
            "markdown": doc.export_to_markdown(),
        }

    def _build_user_message(self, docling_output: dict, pda: PDASchema, pda_categories: list[str]) -> str:
        sections: list[str] = [
            "=== PDA CONTEXT (categories to look for) ===",
            f"Port Call ID: {pda.port_call_id}",
            f"Vessel: {pda.vessel_name}  IMO: {pda.vessel_imo}",
            f"Currency: {pda.currency}",
            "Estimated items:",
        ]
        for item in pda.estimated_items:
            sections.append(
                f"  - {item.category.value}: {item.description} "
                f"({pda.currency} {item.estimated_value * item.quantity:,.2f})"
            )
        sections.append("\n=== FDA DOCUMENT TEXT (Docling extraction) ===")
        sections.append(docling_output["markdown"])

        if docling_output["text_blocks"]:
            sections.append("\n=== BOUNDING BOX DATA ===")
            for block in docling_output["text_blocks"][:100]:
                bb = block["bbox"]
                sections.append(
                    f"[Page {block['page']} | "
                    f"x1={bb['x1']:.1f} y1={bb['y1']:.1f} "
                    f"x2={bb['x2']:.1f} y2={bb['y2']:.1f}] "
                    f"{block['text']}"
                )

        return "\n".join(sections)
