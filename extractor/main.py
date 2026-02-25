"""OpenDA Extractor — internal microservice.

Single endpoint: POST /extract
Accepts a PDF path + PDA JSON, returns FDA JSON.
Never exposed outside the Docker-internal network.
"""

from __future__ import annotations

import logging
import sys

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.schemas.fda import FDASchema
from app.schemas.pda import PDASchema
from app.services.extraction_service import ExtractionService
from app.services.llm_provider import LLMProviderError

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="OpenDA Extractor",
    description="Internal PDF extraction service (Docling + LLM). Not externally exposed.",
    version="1.0.0",
)


# ── Request / Response models ─────────────────────────────────────────────────

class ExtractRequest(BaseModel):
    pdf_path: str
    pda: dict          # raw PDA JSON — validated internally as PDASchema
    job_id: str


class ExtractResponse(BaseModel):
    fda: dict          # validated FDA JSON
    extraction_model: str
    llm_provider: str
    total_actual: float


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "extractor"}


@app.post("/extract", response_model=ExtractResponse)
async def extract(req: ExtractRequest) -> ExtractResponse:
    """Run Docling + LLM extraction on a PDF and return structured FDA JSON."""
    settings = get_settings()

    try:
        pda = PDASchema.model_validate(req.pda)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid PDA: {exc}") from exc

    try:
        service = ExtractionService(settings)
        fda: FDASchema = await service.process_pdf(req.pdf_path, pda, req.job_id)
    except LLMProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Extraction failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ExtractResponse(
        fda=fda.model_dump(),
        extraction_model=fda.extraction_model,
        llm_provider=service._llm.provider_name,
        total_actual=fda.total_actual,
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
