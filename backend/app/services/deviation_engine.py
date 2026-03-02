"""Deviation engine — compares a PDA against an extracted FDA.

Produces a DeviationReport and applies auto-flagging rules:
  - confidence_score < 0.85        → LOW_CONFIDENCE
  - category absent from PDA       → MISSING_PDA_LINE
  - abs_variance > $500 or > 10%   → HIGH_DEVIATION
  - PDA category absent from FDA   → MISSING_FROM_FDA
"""

from __future__ import annotations

import logging

from app.schemas.deviation import (
    DeviationLineItem,
    DeviationReport,
    FlagReasonEnum,
    ItemStatus,
)
from app.schemas.fda import FDASchema
from app.schemas.pda import CategoryEnum, PDASchema

logger = logging.getLogger(__name__)

# ── Flagging thresholds ───────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD = 0.85
ABS_VARIANCE_THRESHOLD = 500.0  # currency units
PCT_VARIANCE_THRESHOLD = 10.0  # percent


class DeviationEngine:
    """Stateless comparison engine — call compare() to get a DeviationReport."""

    def compare(self, pda: PDASchema, fda: FDASchema, da_id: str) -> DeviationReport:
        """Compare PDA estimates against FDA actuals and produce a flagged report.

        Args:
            pda: Validated PDA schema instance.
            fda: Validated FDA schema (AI extraction output).
            da_id: DisbursementAccount DB record ID for the report header.

        Returns:
            DeviationReport with per-line variances and aggregate statistics.
        """
        # ── Build lookup maps ─────────────────────────────────────────────────
        # PDA: category → CostItem (sum quantities × value for comparisons)
        pda_map: dict[CategoryEnum, dict] = {}
        for pda_item in pda.estimated_items:
            cat = pda_item.category
            if cat not in pda_map:
                pda_map[cat] = {
                    "description": pda_item.description,
                    "estimated_value": 0.0,
                }
            pda_map[cat]["estimated_value"] += pda_item.estimated_value * pda_item.quantity

        # FDA: category → ExtractedCostItem (last one wins if duplicates)
        fda_map: dict[CategoryEnum, dict] = {}
        for fda_item in fda.extracted_items:
            cat = fda_item.category
            if cat not in fda_map:
                fda_map[cat] = {
                    "description": fda_item.description,
                    "actual_value": 0.0,
                    "confidence_score": fda_item.confidence_score,
                }
            fda_map[cat]["actual_value"] += fda_item.actual_value
            # Use the minimum confidence score across duplicate categories
            fda_map[cat]["confidence_score"] = min(
                fda_map[cat]["confidence_score"], fda_item.confidence_score
            )

        # ── Build line items for all categories seen in either document ────────
        all_categories = set(pda_map.keys()) | set(fda_map.keys())
        line_items: list[DeviationLineItem] = []

        for cat in sorted(all_categories, key=lambda c: c.value):
            pda_entry = pda_map.get(cat)
            fda_entry = fda_map.get(cat)

            estimated = pda_entry["estimated_value"] if pda_entry else None
            actual = fda_entry["actual_value"] if fda_entry else None
            confidence = fda_entry["confidence_score"] if fda_entry else None

            # ── Compute variances ─────────────────────────────────────────────
            abs_var: float | None = None
            pct_var: float | None = None
            if estimated is not None and actual is not None:
                abs_var = round(actual - estimated, 2)
                pct_var = round((abs_var / estimated) * 100, 2) if estimated != 0 else None

            # ── Apply flagging rules ──────────────────────────────────────────
            flags: list[FlagReasonEnum] = []

            if confidence is not None and confidence < CONFIDENCE_THRESHOLD:
                flags.append(FlagReasonEnum.LOW_CONFIDENCE)

            if pda_entry is None and fda_entry is not None:
                flags.append(FlagReasonEnum.MISSING_PDA_LINE)

            if pda_entry is not None and fda_entry is None:
                flags.append(FlagReasonEnum.MISSING_FROM_FDA)

            if (
                abs_var is not None
                and pct_var is not None
                and (abs(abs_var) > ABS_VARIANCE_THRESHOLD or abs(pct_var) > PCT_VARIANCE_THRESHOLD)
            ):
                flags.append(FlagReasonEnum.HIGH_DEVIATION)

            status = ItemStatus.REQUIRES_REVIEW if flags else ItemStatus.OK

            line_items.append(
                DeviationLineItem(
                    category=cat,
                    pda_description=pda_entry["description"] if pda_entry else None,
                    fda_description=fda_entry["description"] if fda_entry else None,
                    estimated_value=estimated,
                    actual_value=actual,
                    confidence_score=confidence,
                    abs_variance=abs_var,
                    pct_variance=pct_var,
                    status=status,
                    flag_reasons=flags,
                )
            )

        # ── Aggregate statistics ──────────────────────────────────────────────
        total_estimated = round(sum(v["estimated_value"] for v in pda_map.values()), 2)
        total_actual = round(fda.total_actual, 2)
        total_abs_variance = round(total_actual - total_estimated, 2)
        total_pct_variance = (
            round((total_abs_variance / total_estimated) * 100, 2) if total_estimated != 0 else None
        )

        items_not_billed = [cat for cat in pda_map if cat not in fda_map]
        items_not_estimated = [cat for cat in fda_map if cat not in pda_map]
        flagged_count = sum(1 for li in line_items if li.status == ItemStatus.REQUIRES_REVIEW)

        report = DeviationReport(
            port_call_id=pda.port_call_id,
            da_id=da_id,
            line_items=line_items,
            total_estimated=total_estimated,
            total_actual=total_actual,
            total_abs_variance=total_abs_variance,
            total_pct_variance=total_pct_variance,
            items_not_billed=items_not_billed,
            items_not_estimated=items_not_estimated,
            flagged_count=flagged_count,
        )

        logger.info(
            "Deviation report: %d lines, %d flagged, total_variance=%+.2f (%.1f%%)",
            len(line_items),
            flagged_count,
            total_abs_variance,
            total_pct_variance or 0.0,
        )
        return report
