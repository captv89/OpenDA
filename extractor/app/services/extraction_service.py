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

# Number of text blocks to log at DEBUG level for quick bbox sanity checks
_BBOX_DEBUG_SAMPLE = 5

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
3. For pdf_citation_bounding_box:
   - The BOUNDING BOX DATA section below lists every text block with its exact page
     coordinates in PDF point units (origin = bottom-left of page, y increases upward).
   - For each extracted item, find the text block(s) whose text contains the item's
     description or amount and use those EXACT coordinates.
   - Each item MUST have DIFFERENT bounding box coordinates that correspond to WHERE
     that specific line item appears in the document.
   - x1/y1 = bottom-left corner of the text block, x2/y2 = top-right corner.
   - If an item spans multiple blocks, use the block containing its amount/description.
   - Never reuse the same bounding box for different items.
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

        docling_output, raw_doc_dict = self._parse_pdf(pdf_path)
        logger.info("Docling parsed %d pages, %d blocks", docling_output["page_count"], docling_output["block_count"])

        # ── Persist docling raw output for debugging ──────────────────────────
        _save_debug_file(pdf_path, f"{pdf_path.stem}_docling_raw.json", raw_doc_dict)
        _save_debug_file(pdf_path, f"{pdf_path.stem}_docling_blocks.json",
                         {"text_blocks": docling_output["text_blocks"],
                          "tables": docling_output["tables"]})

        # ── Emit a sample of bounding boxes to logs for quick sanity check ───
        sample = docling_output["text_blocks"][:_BBOX_DEBUG_SAMPLE]
        if sample:
            logger.info("BBOX SAMPLE (first %d text blocks):", len(sample))
            for blk in sample:
                bb = blk["bbox"]
                logger.info("  page=%s text=%r  x1=%.1f y1=%.1f x2=%.1f y2=%.1f",
                            blk["page"], blk["text"][:60], bb["x1"], bb["y1"], bb["x2"], bb["y2"])
        else:
            logger.warning("BBOX SAMPLE: no text blocks found — docling may have found no text")

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

        # ── Persist raw LLM response before validation ────────────────────────
        _save_debug_file(pdf_path, f"{pdf_path.stem}_llm_raw.json", raw_json)

        try:
            fda = FDASchema.model_validate_json(raw_json)
        except Exception as exc:
            logger.error("FDA schema validation failed: %s\nRaw: %s…", exc, raw_json[:500])
            raise LLMProviderError(f"LLM returned invalid FDA JSON: {exc}") from exc

        # ── Log bboxes from LLM response so we can compare with docling ───────
        logger.info("LLM BBOX OUTPUT (first %d items):", _BBOX_DEBUG_SAMPLE)
        for item in fda.extracted_items[:_BBOX_DEBUG_SAMPLE]:
            bb = item.pdf_citation_bounding_box
            logger.info("  item=%r  x1=%s y1=%s x2=%s y2=%s",
                        item.description[:50],
                        bb.x1 if bb else "?", bb.y1 if bb else "?",
                        bb.x2 if bb else "?", bb.y2 if bb else "?")

        logger.info("Extraction complete: %d items, total=%.2f, provider=%s",
                    len(fda.extracted_items), fda.total_actual, self._llm.provider_name)
        return fda

    def _parse_pdf(self, pdf_path: Path) -> tuple[dict, dict]:
        """Return (processed_output, raw_doc_dict) from Docling."""
        result = self._converter.convert(str(pdf_path))
        doc = result.document
        doc_dict = doc.export_to_dict()

        text_blocks: list[dict] = []
        page_count = 0
        for page_no, page in enumerate(doc.pages, start=1):
            page_count = max(page_count, page_no)

        # Build page-height lookup so we can convert TOPLEFT → BOTTOMLEFT for
        # table cell bboxes (docling uses TOPLEFT coords for table cells but
        # BOTTOMLEFT for all other document elements).
        page_heights: dict[int, float] = {
            int(k): v["size"]["height"]
            for k, v in doc_dict.get("pages", {}).items()
            if isinstance(v, dict) and "size" in v
        }

        for item in doc_dict.get("texts", []):
            prov = item.get("prov", [{}])[0] if item.get("prov") else {}
            bbox = prov.get("bbox", {})
            text_blocks.append({
                "text": item.get("text", ""),
                "label": item.get("label", "text"),
                "page": prov.get("page_no", 1),
                "bbox": {
                    # Docling uses bottom-left origin: l=left, r=right, b=bottom, t=top
                    # b < t (bottom is a lower y value than top)
                    "x1": bbox.get("l", 0.0), "y1": bbox.get("b", 0.0),
                    "x2": bbox.get("r", 0.0), "y2": bbox.get("t", 0.0),
                },
            })

        tables: list[dict] = []
        for table in doc_dict.get("tables", []):
            prov = table.get("prov", [{}])[0] if table.get("prov") else {}
            tbl_bbox_raw = prov.get("bbox", {})
            page_no = prov.get("page_no", 1)

            # ── Group cells by their canonical row index ──────────────────────
            # Docling may repeat a spanned cell in multiple grid positions, so
            # deduplicate by start_row_offset_idx (canonical row of each cell).
            row_map: dict[int, list[dict]] = {}
            all_cell_texts: list[str] = []

            for grid_row_idx, row in enumerate(table.get("data", {}).get("grid", [])):
                for cell in row:
                    if not cell:
                        continue
                    text = (cell.get("text") or "").strip()
                    if text:
                        all_cell_texts.append(text)
                    canonical_row = cell.get("start_row_offset_idx", grid_row_idx)
                    row_map.setdefault(canonical_row, []).append(cell)

            # ── Try to build per-row text blocks from cell-level bboxes ───────
            # When docling recognises a table structure in the PDF it attaches
            # individual bounding boxes to each cell.  We merge all cells in a
            # row into one entry so the LLM gets a distinct coordinate anchor
            # per cost-item row (instead of one coarse table-level bbox).
            has_cell_bboxes = False
            seen_row_texts: set[str] = set()  # dedup span-repeated rows

            for ri, cells_in_row in sorted(row_map.items()):
                row_texts = [c.get("text", "").strip() for c in cells_in_row if (c.get("text") or "").strip()]
                row_key = " | ".join(row_texts)
                if not row_texts or row_key in seen_row_texts:
                    continue
                seen_row_texts.add(row_key)

                cell_bboxes = [c.get("bbox", {}) for c in cells_in_row if c.get("bbox")]
                if cell_bboxes:
                    has_cell_bboxes = True
                    ph = page_heights.get(page_no, 842.0)
                    # Normalise every cell bbox to BOTTOMLEFT before merging.
                    # Docling emits table-cell bboxes in TOPLEFT origin (y=0 at
                    # top of page, y increases downward) while all other elements
                    # use BOTTOMLEFT origin.  The frontend renderer expects
                    # BOTTOMLEFT everywhere, so we convert here.
                    norm = [_bbox_to_bottomleft(b, ph) for b in cell_bboxes]
                    text_blocks.append({
                        "text": "  |  ".join(row_texts),
                        "label": "table_row",
                        "page": page_no,
                        "bbox": {
                            # Merge all cells in the row into a single spanning bbox
                            "x1": min(b["x1"] for b in norm),
                            "y1": min(b["y1"] for b in norm),
                            "x2": max(b["x2"] for b in norm),
                            "y2": max(b["y2"] for b in norm),
                        },
                    })

            # ── Fallback: no cell-level bboxes → one block for the whole table ─
            # This happens for scanned/image tables where docling cannot determine
            # per-cell coordinates.  We still expose the text so the LLM sees it,
            # but all items sharing this table will get the same coarse bbox.
            if not has_cell_bboxes and all_cell_texts:
                logger.warning(
                    "Table on page %d has no cell-level bboxes "
                    "(scanned image table?); using whole-table bbox as fallback",
                    page_no,
                )
                text_blocks.append({
                    "text": " | ".join(all_cell_texts),
                    "label": "table",
                    "page": page_no,
                    "bbox": {
                        "x1": tbl_bbox_raw.get("l", 0.0), "y1": tbl_bbox_raw.get("b", 0.0),
                        "x2": tbl_bbox_raw.get("r", 0.0), "y2": tbl_bbox_raw.get("t", 0.0),
                    },
                })

            tables.append({
                "page": page_no,
                "cells": all_cell_texts,
                "bbox": {
                    "x1": tbl_bbox_raw.get("l", 0.0), "y1": tbl_bbox_raw.get("b", 0.0),
                    "x2": tbl_bbox_raw.get("r", 0.0), "y2": tbl_bbox_raw.get("t", 0.0),
                },
            })

        return {
            "page_count": page_count or 1,
            "block_count": len(text_blocks),
            "text_blocks": text_blocks,
            "tables": tables,
            "markdown": doc.export_to_markdown(),
        }, doc_dict  # second element is the raw Docling export for debugging

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
            sections.append(
                "\n=== BOUNDING BOX DATA ===\n"
                "Each line below shows a text block with its EXACT PDF coordinates.\n"
                "Coordinates use bottom-left page origin; x1/y1 = bottom-left corner, x2/y2 = top-right corner.\n"
                "Match each extracted cost item to the block(s) containing its description or amount\n"
                "and copy those coordinates verbatim into pdf_citation_bounding_box.\n"
                "Items labelled 'table_row' are individual rows extracted from detected tables — "
                "these are the most relevant anchors for cost line items.\n"
            )
            for block in docling_output["text_blocks"]:
                bb = block["bbox"]
                sections.append(
                    f"[Page {block['page']} | label={block['label']} | "
                    f"x1={bb['x1']:.1f} y1={bb['y1']:.1f} "
                    f"x2={bb['x2']:.1f} y2={bb['y2']:.1f}] "
                    f"{block['text']}"
                )
        else:
            sections.append(
                "\n=== BOUNDING BOX DATA ===\n"
                "WARNING: No bounding box coordinates could be extracted from this PDF "
                "(likely a pure image/scan with no machine-readable text layer).\n"
                "You MUST still populate pdf_citation_bounding_box for each item, but use "
                "estimated coordinates that are visually distinct (different y1/y2 per row) "
                "rather than identical values.  Set confidence_score ≤ 0.6 for all items.\n"
            )

        return "\n".join(sections)


# ── Module-level debug helper ─────────────────────────────────────────────────

def _bbox_to_bottomleft(bbox: dict, page_height: float) -> dict:
    """Convert a Docling bbox dict to BOTTOMLEFT-origin {x1, y1, x2, y2}.

    Docling uses BOTTOMLEFT for text elements (b < t, y increases upward) but
    TOPLEFT for table-cell elements (t < b, y increases downward).  We detect
    which system is in use via the ``coord_origin`` key and convert accordingly
    so that all bboxes reaching the frontend share the same coordinate space.
    """
    origin = bbox.get("coord_origin", "BOTTOMLEFT").upper()
    l, r = bbox.get("l", 0.0), bbox.get("r", 0.0)
    t, b = bbox.get("t", 0.0), bbox.get("b", 0.0)

    if origin == "TOPLEFT":
        # t and b are distances from the top; convert to BOTTOMLEFT y-values.
        # In TOPLEFT: t < b  (t is nearer the top).
        # In BOTTOMLEFT: y_bottom = page_height - b_topleft
        #                y_top    = page_height - t_topleft
        y1 = page_height - b   # bottom edge in BOTTOMLEFT coords (smaller y)
        y2 = page_height - t   # top    edge in BOTTOMLEFT coords (larger y)
    else:
        # Already BOTTOMLEFT: b = bottom (smaller y), t = top (larger y)
        y1, y2 = b, t

    return {"x1": l, "y1": y1, "x2": r, "y2": y2}


def _save_debug_file(pdf_path: Path, filename: str, data: object) -> None:
    """Persist *data* as JSON next to the PDF for post-hoc debugging.

    Saves to the same directory as the PDF so debug files are co-located
    with the source document.  Failures are logged but never re-raised so
    they cannot break the main extraction flow.
    """
    out_path = pdf_path.parent / filename
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = data if isinstance(data, str) else json.dumps(data, indent=2, default=str)
        out_path.write_text(payload, encoding="utf-8")
        logger.info("DEBUG file saved: %s", out_path)
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not save debug file %s: %s", out_path, exc)
