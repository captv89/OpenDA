"""Synthetic test data generator for OpenDA.

Generates:
  - test_data/pda_001.json … pda_005.json  (Proforma DAs)
  - test_data/fda_pdfs/fda_001.pdf … fda_005.pdf  (FDA PDFs via reportlab)

Scenarios
---------
001  Clean match        — All items match within 5 %, high confidence
002  Over-billing       — TOWAGE billed +25 % above estimate
003  Missing item       — WASTE_DISPOSAL absent from FDA (items_not_billed)
004  Low-confidence     — LAUNCH_HIRE on a handwritten-style page (score 0.62)
005  Multi-flag         — HIGH_DEVIATION on PORT_DUES + missing AGENCY_FEE

Run from the repo root:
    python test_data/generate_fixtures.py
"""

from __future__ import annotations

import json
import math
import os
import random
import sys
from pathlib import Path

# ── Path wiring so schemas are importable without installing the package ──────
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

# ── Output directories ────────────────────────────────────────────────────────
TEST_DATA = Path(__file__).resolve().parent
FDA_PDFS = TEST_DATA / "fda_pdfs"
FDA_PDFS.mkdir(parents=True, exist_ok=True)

random.seed(42)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _pda(
    index: int,
    port_code: str,
    vessel: str,
    imo: str,
    currency: str,
    items: list[dict],
    valid_until: str,
) -> dict:
    """Build a PDA dict that satisfies PDASchema, computing total automatically."""
    total = round(sum(i["estimated_value"] * i.get("quantity", 1.0) for i in items), 2)
    return {
        "port_call_id": f"PC-2025-{port_code}-{index:04d}",
        "vessel_name": vessel,
        "vessel_imo": imo,
        "port_code": port_code,
        "currency": currency,
        "estimated_items": items,
        "total_estimated": total,
        "valid_until": valid_until,
        "prepared_by": "OpenDA Test Agent",
    }


def _save_pda(index: int, data: dict) -> None:
    path = TEST_DATA / f"pda_{index:03d}.json"
    path.write_text(json.dumps(data, indent=2, default=str))
    print(f"  ✓ {path.name}")


# ── PDA Fixtures ──────────────────────────────────────────────────────────────

PDAS: list[dict] = [
    # 001 — Clean match scenario
    _pda(
        1,
        "SGSIN",
        "MT PACIFIC STAR",
        "9321483",
        "USD",
        [
            {"category": "PILOTAGE", "description": "Inward / Outward pilotage", "estimated_value": 1200.00, "unit": "per_movement", "quantity": 2},
            {"category": "TOWAGE", "description": "Towage 2 tugs × 2 movements", "estimated_value": 3500.00, "unit": "per_movement", "quantity": 4},
            {"category": "PORT_DUES", "description": "Port dues per GRT", "estimated_value": 4800.00, "unit": "lump_sum", "quantity": 1},
            {"category": "AGENCY_FEE", "description": "Agency fee — port call", "estimated_value": 850.00, "unit": "lump_sum", "quantity": 1},
            {"category": "LAUNCH_HIRE", "description": "Crew change launch hire", "estimated_value": 320.00, "unit": "per_hour", "quantity": 3},
            {"category": "WASTE_DISPOSAL", "description": "MARPOL garbage disposal", "estimated_value": 450.00, "unit": "lump_sum", "quantity": 1},
        ],
        "2025-06-30",
    ),
    # 002 — Over-billing: TOWAGE is billed +25 % above estimate
    _pda(
        2,
        "MYPEN",
        "MT ORIENT GLORY",
        "9456781",
        "USD",
        [
            {"category": "PILOTAGE", "description": "Pilotage — inward", "estimated_value": 950.00, "unit": "per_movement", "quantity": 1},
            {"category": "TOWAGE", "description": "Towage 1 tug inward", "estimated_value": 2800.00, "unit": "per_movement", "quantity": 1},
            {"category": "PORT_DUES", "description": "Port dues", "estimated_value": 3200.00, "unit": "lump_sum", "quantity": 1},
            {"category": "AGENCY_FEE", "description": "Agency fee", "estimated_value": 750.00, "unit": "lump_sum", "quantity": 1},
            {"category": "WASTE_DISPOSAL", "description": "Sludge disposal", "estimated_value": 380.00, "unit": "lump_sum", "quantity": 1},
        ],
        "2025-07-15",
    ),
    # 003 — Missing item: WASTE_DISPOSAL has no FDA evidence
    _pda(
        3,
        "AEJEA",
        "MT ARABIAN WIND",
        "9512347",
        "USD",
        [
            {"category": "PILOTAGE", "description": "Inward/outward pilotage", "estimated_value": 1100.00, "unit": "per_movement", "quantity": 2},
            {"category": "TOWAGE", "description": "Towage 2 tugs", "estimated_value": 4200.00, "unit": "per_movement", "quantity": 2},
            {"category": "PORT_DUES", "description": "Light dues + port dues", "estimated_value": 5500.00, "unit": "lump_sum", "quantity": 1},
            {"category": "AGENCY_FEE", "description": "Agency fee", "estimated_value": 900.00, "unit": "lump_sum", "quantity": 1},
            {"category": "WASTE_DISPOSAL", "description": "MARPOL waste — bilge water", "estimated_value": 620.00, "unit": "lump_sum", "quantity": 1},
        ],
        "2025-08-01",
    ),
    # 004 — Low confidence: LAUNCH_HIRE from handwritten chit (score 0.62)
    _pda(
        4,
        "NLRTM",
        "MT NORTH SEA TRADER",
        "9634521",
        "EUR",
        [
            {"category": "PILOTAGE", "description": "Pilotage inward + outward", "estimated_value": 1350.00, "unit": "per_movement", "quantity": 2},
            {"category": "TOWAGE", "description": "Towage 2 tugs × 2 moves", "estimated_value": 5200.00, "unit": "per_movement", "quantity": 4},
            {"category": "PORT_DUES", "description": "Port dues GRT-based", "estimated_value": 6800.00, "unit": "lump_sum", "quantity": 1},
            {"category": "AGENCY_FEE", "description": "Port agency fee", "estimated_value": 1100.00, "unit": "lump_sum", "quantity": 1},
            {"category": "LAUNCH_HIRE", "description": "Launch hire — crew boat", "estimated_value": 480.00, "unit": "per_hour", "quantity": 4},
        ],
        "2025-08-20",
    ),
    # 005 — Multi-flag: PORT_DUES +18 % deviation + AGENCY_FEE missing from FDA
    _pda(
        5,
        "JPYOK",
        "MT EASTERN HORIZON",
        "9741236",
        "USD",
        [
            {"category": "PILOTAGE", "description": "Pilotage fee", "estimated_value": 1050.00, "unit": "per_movement", "quantity": 2},
            {"category": "TOWAGE", "description": "Tugboat hire 2 movements", "estimated_value": 3100.00, "unit": "per_movement", "quantity": 2},
            {"category": "PORT_DUES", "description": "Port dues — berth dues", "estimated_value": 7200.00, "unit": "lump_sum", "quantity": 1},
            {"category": "AGENCY_FEE", "description": "Agency disbursements fee", "estimated_value": 980.00, "unit": "lump_sum", "quantity": 1},
            {"category": "WASTE_DISPOSAL", "description": "Waste reception facility", "estimated_value": 290.00, "unit": "lump_sum", "quantity": 1},
        ],
        "2025-09-05",
    ),
]


# ── PDF generation helpers ────────────────────────────────────────────────────

PAGE_W, PAGE_H = A4


def _header(c: canvas.Canvas, title: str, vessel: str, port_call_id: str) -> float:
    """Draw a standard invoice header. Returns the y-cursor after the header."""
    c.setFillColor(colors.HexColor("#1a3a5c"))
    c.rect(0, PAGE_H - 60 * mm, PAGE_W, 60 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(20 * mm, PAGE_H - 22 * mm, title)
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, PAGE_H - 32 * mm, f"Vessel: {vessel}")
    c.drawString(20 * mm, PC_Y := PAGE_H - 40 * mm, f"Port Call ID: {port_call_id}")
    _ = PC_Y
    c.setFillColor(colors.black)
    return PAGE_H - 70 * mm


def _table_row(
    c: canvas.Canvas,
    y: float,
    cols: list[str],
    widths: list[float],
    x0: float = 20 * mm,
    bold: bool = False,
    bg: colors.Color | None = None,
) -> float:
    """Draw a single table row. Returns y after the row."""
    row_h = 8 * mm
    if bg:
        c.setFillColor(bg)
        c.rect(x0, y - row_h, sum(widths), row_h, fill=1, stroke=0)
        c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold" if bold else "Helvetica", 9)
    x = x0
    for text, w in zip(cols, widths):
        c.drawString(x + 2 * mm, y - 6 * mm, str(text))
        x += w
    c.setStrokeColor(colors.HexColor("#cccccc"))
    c.line(x0, y - row_h, x0 + sum(widths), y - row_h)
    return y - row_h


def _footer(c: canvas.Canvas, page_call_id: str) -> None:
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.grey)
    c.drawString(20 * mm, 10 * mm, f"OpenDA Synthetic Test Document | {page_call_id} | Page 1")


COL_WIDTHS = [60 * mm, 50 * mm, 35 * mm, 25 * mm]  # Desc, Category, Amount, Doc Type


def _build_clean_pdf(
    path: Path,
    pda: dict,
    items: list[dict],
    scenario_label: str,
) -> None:
    """Generate a clean digital-invoice style FDA PDF."""
    c = canvas.Canvas(str(path), pagesize=A4)
    y = _header(c, "FINAL DISBURSEMENT ACCOUNT", pda["vessel_name"], pda["port_call_id"])
    y -= 5 * mm
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, y, f"Scenario: {scenario_label}   |   Currency: {pda['currency']}")
    y -= 8 * mm

    y = _table_row(c, y, ["Description", "Category", "Amount", "Doc Type"],
                   COL_WIDTHS, bold=True,
                   bg=colors.HexColor("#e8f0fe"))
    for item in items:
        y = _table_row(
            c, y,
            [item["description"], item["category"],
             f"{pda['currency']} {item['actual_value']:,.2f}", item["doc_type"]],
            COL_WIDTHS,
        )
        if y < 40 * mm:
            c.showPage()
            y = PAGE_H - 20 * mm

    y -= 5 * mm
    c.setFont("Helvetica-Bold", 10)
    total = sum(i["actual_value"] for i in items)
    c.drawString(20 * mm, y, f"TOTAL:  {pda['currency']} {total:,.2f}")
    _footer(c, pda["port_call_id"])
    c.save()


def _build_lowcontrast_pdf(
    path: Path,
    pda: dict,
    items: list[dict],
) -> None:
    """Generate a low-contrast 'scanned receipt' style FDA PDF."""
    c = canvas.Canvas(str(path), pagesize=A4)
    # Washed-out background
    c.setFillColor(colors.HexColor("#f5f0e8"))
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    y = PAGE_H - 30 * mm
    c.setFillColor(colors.HexColor("#888888"))  # low-contrast text
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, y, "PORT DISBURSEMENT ACCOUNT (SCANNED COPY)")
    y -= 8 * mm
    c.setFont("Helvetica", 8)
    c.drawString(20 * mm, y, f"Vessel: {pda['vessel_name']}   Port Call: {pda['port_call_id']}")
    y -= 10 * mm

    for item in items:
        is_handwritten = item.get("handwritten", False)
        if is_handwritten:
            c.setFont("Courier-Oblique", 8)  # simulate handwriting
            c.setFillColor(colors.HexColor("#4a4a8a"))
        else:
            c.setFont("Helvetica", 8)
            c.setFillColor(colors.HexColor("#888888"))

        # Add slight rotation to simulate scanning skew
        angle = random.uniform(-0.5, 0.5)
        c.saveState()
        c.rotate(angle)
        c.drawString(
            20 * mm,
            y,
            f"{item['category']:20s}  {item['description'][:35]:35s}  "
            f"{pda['currency']} {item['actual_value']:>10,.2f}",
        )
        c.restoreState()
        y -= 7 * mm

    y -= 5 * mm
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.HexColor("#666666"))
    total = sum(i["actual_value"] for i in items)
    c.drawString(20 * mm, y, f"TOTAL  {pda['currency']} {total:,.2f}")
    _footer(c, pda["port_call_id"])
    c.save()


# ── FDA data definitions ──────────────────────────────────────────────────────

FDA_ITEMS: list[list[dict]] = [
    # 001 — Clean match (slight rounding differences only)
    [
        {"category": "PILOTAGE", "description": "Inward / Outward pilotage", "actual_value": 2418.00, "doc_type": "OFFICIAL_RECEIPT", "handwritten": False},
        {"category": "TOWAGE", "description": "Towage 4 movements", "actual_value": 14035.00, "doc_type": "DIGITAL_INVOICE", "handwritten": False},
        {"category": "PORT_DUES", "description": "Port dues per GRT", "actual_value": 4823.50, "doc_type": "OFFICIAL_RECEIPT", "handwritten": False},
        {"category": "AGENCY_FEE", "description": "Agency fee — port call", "actual_value": 850.00, "doc_type": "DIGITAL_INVOICE", "handwritten": False},
        {"category": "LAUNCH_HIRE", "description": "Crew change launch hire 3h", "actual_value": 960.00, "doc_type": "SCANNED_RECEIPT", "handwritten": False},
        {"category": "WASTE_DISPOSAL", "description": "MARPOL garbage disposal", "actual_value": 452.00, "doc_type": "OFFICIAL_RECEIPT", "handwritten": False},
    ],
    # 002 — Over-billing: TOWAGE is 25 % above PDA estimate (2800 → 3500)
    [
        {"category": "PILOTAGE", "description": "Pilotage inward", "actual_value": 953.00, "doc_type": "OFFICIAL_RECEIPT", "handwritten": False},
        {"category": "TOWAGE", "description": "Towage 1 tug inward — REVISED RATE", "actual_value": 3500.00, "doc_type": "DIGITAL_INVOICE", "handwritten": False},
        {"category": "PORT_DUES", "description": "Port dues", "actual_value": 3198.00, "doc_type": "OFFICIAL_RECEIPT", "handwritten": False},
        {"category": "AGENCY_FEE", "description": "Agency fee", "actual_value": 752.00, "doc_type": "DIGITAL_INVOICE", "handwritten": False},
        {"category": "WASTE_DISPOSAL", "description": "Sludge disposal", "actual_value": 381.00, "doc_type": "SCANNED_RECEIPT", "handwritten": False},
    ],
    # 003 — Missing item: WASTE_DISPOSAL not present in FDA
    [
        {"category": "PILOTAGE", "description": "Inward/outward pilotage", "actual_value": 2204.00, "doc_type": "OFFICIAL_RECEIPT", "handwritten": False},
        {"category": "TOWAGE", "description": "Towage 2 tugs × 2 mvts", "actual_value": 8415.00, "doc_type": "DIGITAL_INVOICE", "handwritten": False},
        {"category": "PORT_DUES", "description": "Light dues + port dues", "actual_value": 5512.00, "doc_type": "OFFICIAL_RECEIPT", "handwritten": False},
        {"category": "AGENCY_FEE", "description": "Agency fee", "actual_value": 900.00, "doc_type": "DIGITAL_INVOICE", "handwritten": False},
        # WASTE_DISPOSAL intentionally absent
    ],
    # 004 — Low confidence: LAUNCH_HIRE from handwritten chit
    [
        {"category": "PILOTAGE", "description": "Pilotage inward + outward", "actual_value": 2702.00, "doc_type": "OFFICIAL_RECEIPT", "handwritten": False},
        {"category": "TOWAGE", "description": "Towage 4 movements", "actual_value": 20815.00, "doc_type": "DIGITAL_INVOICE", "handwritten": False},
        {"category": "PORT_DUES", "description": "Port dues GRT-based", "actual_value": 6834.00, "doc_type": "OFFICIAL_RECEIPT", "handwritten": False},
        {"category": "AGENCY_FEE", "description": "Port agency fee", "actual_value": 1100.00, "doc_type": "DIGITAL_INVOICE", "handwritten": False},
        {"category": "LAUNCH_HIRE", "description": "Launch hire — crew boat 4h", "actual_value": 485.00, "doc_type": "HANDWRITTEN_CHIT", "handwritten": True},
    ],
    # 005 — Multi-flag: PORT_DUES +18 % AND AGENCY_FEE absent
    [
        {"category": "PILOTAGE", "description": "Pilotage fee × 2", "actual_value": 2103.00, "doc_type": "OFFICIAL_RECEIPT", "handwritten": False},
        {"category": "TOWAGE", "description": "Tugboat hire 2 movements", "actual_value": 6215.00, "doc_type": "DIGITAL_INVOICE", "handwritten": False},
        {"category": "PORT_DUES", "description": "Port dues — berth dues REVISED", "actual_value": 8496.00, "doc_type": "OFFICIAL_RECEIPT", "handwritten": False},  # +18% on 7200
        {"category": "WASTE_DISPOSAL", "description": "Waste reception facility", "actual_value": 291.00, "doc_type": "SCANNED_RECEIPT", "handwritten": False},
        # AGENCY_FEE intentionally absent
    ],
]

SCENARIO_LABELS = [
    "Clean Match — all items within ±5%",
    "Over-billing — TOWAGE billed +25% above estimate",
    "Missing Item — WASTE_DISPOSAL absent from FDA",
    "Low Confidence — LAUNCH_HIRE from handwritten chit",
    "Multi-Flag — PORT_DUES +18% deviation + AGENCY_FEE missing",
]


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    print("\nGenerating OpenDA synthetic test fixtures...\n")

    for i, (pda, fda_items, label) in enumerate(zip(PDAS, FDA_ITEMS, SCENARIO_LABELS), start=1):
        # Save PDA JSON
        _save_pda(i, pda)

        # Generate FDA PDF
        pdf_path = FDA_PDFS / f"fda_{i:03d}.pdf"

        # Scenarios 003 & 004 get the low-contrast scanned style
        use_lowcontrast = i in (3, 4)
        if use_lowcontrast:
            _build_lowcontrast_pdf(pdf_path, pda, fda_items)
        else:
            _build_clean_pdf(pdf_path, pda, fda_items, label)

        print(f"  ✓ fda_{i:03d}.pdf  [{label}]")

    print(f"\n✅ Done — {len(PDAS)} PDA JSONs + {len(FDA_ITEMS)} FDA PDFs written to {TEST_DATA}\n")


if __name__ == "__main__":
    main()
