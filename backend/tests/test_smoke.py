"""Smoke tests — verify FastAPI app starts and health endpoint responds."""

import pytest
from httpx import ASGITransport, AsyncClient

# Import the app using a try/except so the test file is importable
# even if optional deps aren't available in the test environment
try:
    from main import app

    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False


@pytest.mark.skipif(not APP_AVAILABLE, reason="App dependencies not installed")
@pytest.mark.asyncio
async def test_health_endpoint_structure():
    """Health endpoint returns expected JSON keys."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:  # type: ignore[arg-type]
        response = await client.get("/api/v1/health")

    # Accept 200 (all healthy) or 503 (DB/Redis not running in test env)
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
    assert "llm_model" in data


def test_schemas_importable():
    """All Pydantic schemas can be imported without errors."""
    from app.schemas.deviation import DeviationReport  # noqa: F401
    from app.schemas.fda import FDASchema  # noqa: F401
    from app.schemas.pda import PDASchema  # noqa: F401


def test_pda_schema_validate():
    """PDASchema validates a minimal valid payload."""
    from pathlib import Path

    from app.schemas.pda import PDASchema

    fixture_path = Path(__file__).parent.parent.parent / "test_data" / "pda_001.json"
    if not fixture_path.exists():
        pytest.skip("Fixture not generated — run generate_fixtures.py first")

    pda = PDASchema.model_validate_json(fixture_path.read_text())
    assert pda.port_call_id.startswith("PC-")
    assert len(pda.cost_items) > 0
