"""Deviation engine unit tests — pure Python, no DB required."""

import datetime

import pytest

from app.schemas.deviation import FlagReasonEnum
from app.services.deviation_engine import DeviationEngine


@pytest.fixture
def engine():
    return DeviationEngine()


# ── Shared fixture helpers ────────────────────────────────────────────────────

_BBOX = {"page": 1, "x1": 10.0, "y1": 10.0, "x2": 200.0, "y2": 30.0}


def _extracted_item(category: str, description: str, actual_value: float, confidence: float = 0.95):
    return {
        "category": category,
        "description": description,
        "actual_value": actual_value,
        "currency": "USD",
        "confidence_score": confidence,
        "pdf_citation_bounding_box": _BBOX,
        "supporting_document_type": "DIGITAL_INVOICE",
    }


def _pda_item(category: str, description: str, estimated_value: float, quantity: float = 1.0):
    return {
        "category": category,
        "description": description,
        "estimated_value": estimated_value,
        "unit": "lump_sum",
        "quantity": quantity,
    }


def _make_pda(items: list[dict]):
    from app.schemas.pda import PDASchema

    total = sum(i["estimated_value"] * i.get("quantity", 1.0) for i in items)
    return PDASchema.model_validate(
        {
            "port_call_id": "PC-2024-SGSIN-0001",
            "vessel_name": "MV Test Vessel",
            "vessel_imo": "1234567",
            "port_code": "SGSIN",
            "currency": "USD",
            "estimated_items": items,
            "total_estimated": total,
            "valid_until": str(datetime.date.today()),
        }
    )


def _make_fda(items: list[dict]):
    from app.schemas.fda import FDASchema

    total = sum(i["actual_value"] for i in items)
    return FDASchema.model_validate(
        {
            "port_call_id": "PC-2024-SGSIN-0001",
            "processing_job_id": "test-job-001",
            "extracted_items": items,
            "total_actual": total,
        }
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_exact_match_no_flags(engine):
    """Items that match exactly within thresholds produce no flags."""
    pda = _make_pda([_pda_item("PILOTAGE", "Inward pilot", 500.0)])
    fda = _make_fda([_extracted_item("PILOTAGE", "Inward pilot", 500.0, confidence=0.95)])
    report = engine.compare(pda, fda, "da-test-001")
    flagged = [i for i in report.line_items if i.flag_reasons]
    assert len(flagged) == 0


def test_high_deviation_flagged(engine):
    """Items with >10% variance are flagged HIGH_DEVIATION."""
    pda = _make_pda([_pda_item("TOWAGE", "Tug services", 1000.0)])
    fda = _make_fda([_extracted_item("TOWAGE", "Tug services", 1200.0)])
    report = engine.compare(pda, fda, "da-test-002")
    assert any(FlagReasonEnum.HIGH_DEVIATION in i.flag_reasons for i in report.line_items)


def test_low_confidence_flagged(engine):
    """Items with confidence < 0.85 are flagged LOW_CONFIDENCE."""
    pda = _make_pda([_pda_item("PORT_DUES", "Port dues", 800.0)])
    fda = _make_fda([_extracted_item("PORT_DUES", "Port dues", 800.0, confidence=0.70)])
    report = engine.compare(pda, fda, "da-test-004")
    dues = next((i for i in report.line_items if i.category == "PORT_DUES"), None)
    assert dues is not None
    assert FlagReasonEnum.LOW_CONFIDENCE in dues.flag_reasons


def test_missing_pda_line_flagged(engine):
    """FDA items with no corresponding PDA category get MISSING_PDA_LINE."""
    pda = _make_pda([_pda_item("PILOTAGE", "Pilot", 300.0)])
    fda = _make_fda(
        [
            _extracted_item("PILOTAGE", "Pilot", 300.0),
            _extracted_item("AGENCY_FEE", "Agency fee", 800.0),
        ]
    )
    report = engine.compare(pda, fda, "da-test-003")
    agency = next((i for i in report.line_items if i.category == "AGENCY_FEE"), None)
    assert agency is not None
    assert FlagReasonEnum.MISSING_PDA_LINE in agency.flag_reasons


def test_missing_from_fda_flagged(engine):
    """PDA item absent from FDA gets MISSING_FROM_FDA on the report."""
    pda = _make_pda(
        [
            _pda_item("PILOTAGE", "Pilot", 300.0),
            _pda_item("LAUNCH_HIRE", "Launch hire", 200.0),
        ]
    )
    fda = _make_fda([_extracted_item("PILOTAGE", "Pilot", 300.0)])
    report = engine.compare(pda, fda, "da-test-005")
    launch = next((i for i in report.line_items if i.category == "LAUNCH_HIRE"), None)
    assert launch is not None
    assert FlagReasonEnum.MISSING_FROM_FDA in launch.flag_reasons
