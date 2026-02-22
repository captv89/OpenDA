"""Quick smoke test for Phase 1 schemas."""
import json
import sys
sys.path.insert(0, "backend")

from app.schemas.pda import PDASchema, CategoryEnum
from app.schemas.fda import FDASchema, BoundingBox, ExtractedCostItem
from app.schemas.deviation import DeviationReport, FlagReasonEnum

# ── PDA roundtrip ─────────────────────────────────────────────────────────────
pda_data = {
    "port_call_id": "PC-2025-SGSIN-0001",
    "vessel_name": "MT TEST",
    "vessel_imo": "9321483",
    "port_code": "SGSIN",
    "currency": "USD",
    "estimated_items": [
        {"category": "PILOTAGE", "description": "Pilotage", "estimated_value": 1000.0, "unit": "lump_sum", "quantity": 1},
        {"category": "TOWAGE",   "description": "Towage",   "estimated_value": 2500.0, "unit": "per_movement", "quantity": 2},
    ],
    "total_estimated": 6000.0,  # 1000 + 2500*2 = 6000
    "valid_until": "2025-12-31",
}
pda = PDASchema.model_validate(pda_data)
print(f"PDA schema OK — total_estimated: {pda.total_estimated}")

# ── PDA validator catches wrong total ─────────────────────────────────────────
try:
    bad = {**pda_data, "total_estimated": 999.0}
    PDASchema.model_validate(bad)
    print("FAIL — should have raised ValueError")
except Exception as e:
    print(f"PDA total validator OK — caught: {str(e)[:80]}")

# ── FDA roundtrip ─────────────────────────────────────────────────────────────
fda_data = {
    "port_call_id": "PC-2025-SGSIN-0001",
    "processing_job_id": "job-abc",
    "extracted_items": [
        {
            "category": "PILOTAGE",
            "description": "Pilotage inward",
            "actual_value": 1020.0,
            "currency": "USD",
            "confidence_score": 0.97,
            "pdf_citation_bounding_box": {"page": 1, "x1": 10.0, "y1": 20.0, "x2": 200.0, "y2": 35.0},
            "supporting_document_type": "OFFICIAL_RECEIPT",
        }
    ],
    "total_actual": 1020.0,
}
fda = FDASchema.model_validate(fda_data)
print(f"FDA schema OK — confidence_score: {fda.extracted_items[0].confidence_score}")

# ── JSON Schema export (for LLM prompt injection) ─────────────────────────────
schema_str = json.dumps(FDASchema.model_json_schema(), indent=2)
print(f"FDA JSON Schema export OK — {len(schema_str)} chars")

# ── Confidence validator ──────────────────────────────────────────────────────
try:
    ExtractedCostItem.model_validate({**fda_data["extracted_items"][0], "confidence_score": 1.5})
    print("FAIL — should have raised")
except Exception as e:
    print(f"Confidence validator OK — caught: {str(e)[:80]}")

# ── BoundingBox x2/y2 validator ───────────────────────────────────────────────
try:
    BoundingBox(page=1, x1=100.0, y1=20.0, x2=50.0, y2=35.0)  # x2 < x1
    print("FAIL — should have raised")
except Exception as e:
    print(f"BoundingBox validator OK — caught: {str(e)[:80]}")

# ── Deviation schema import ───────────────────────────────────────────────────
print(f"DeviationReport fields: {list(DeviationReport.model_fields.keys())}")
print(f"FlagReasonEnum values: {[e.value for e in FlagReasonEnum]}")

print("\nAll schema smoke tests passed. ✓")
