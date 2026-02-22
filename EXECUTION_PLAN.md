# OpenDA — Execution Plan

**Stack decisions confirmed:**
- Python: UV + `pyproject.toml` (no `requirements.txt`)
- React: pnpm workspace monorepo (both frontends under one `pnpm-workspace.yaml`)
- Auth: Skipped for MVP — two hardcoded identities (`accountant-001`, `operator-001`) passed as a static header `X-User-Id`
- Build scope: All 6 phases

---

## Progress Tracker

| Phase | Title | Status |
|-------|-------|--------|
| 0 | Monorepo Scaffold | ✅ Complete |
| 1 | Data Modeling & Synthetic Assets | 🔄 In Progress |
| 2 | Backend API & AI Engine | ⬜ Not Started |
| 3 | Workflow State Machine | ⬜ Not Started |
| 4 | Accountant React App | ⬜ Not Started |
| 5 | Operator React App | ⬜ Not Started |
| 6 | Packaging & Launch Assets | ⬜ Not Started |

---

## Phase 0 — Monorepo Scaffold *(prerequisite, ~30 min)*

Before any code is written, establish the exact folder skeleton and tooling configs.

| Step | Action | Status |
|------|--------|--------|
| 0.1 | `git init openda`, add `.gitignore` for Python, Node, Docker artefacts | ✅ |
| 0.2 | Create top-level `pnpm-workspace.yaml` declaring `frontend-accountant` and `frontend-operator` as workspace packages | ✅ |
| 0.3 | Create `backend/pyproject.toml` with UV, declaring all Python deps from §3.7 of the spec, using `[project.optional-dependencies]` for dev/test groups | ✅ |
| 0.4 | Create `.env.example` with all required keys: `ANTHROPIC_API_KEY`, `DATABASE_URL`, `REDIS_URL`, `WEBHOOK_URL`, `UPLOAD_DIR` | ✅ |
| 0.5 | Create top-level `docker-compose.yml` with service stubs (postgres, redis, backend, celery-worker, frontend-accountant, frontend-operator) — filled out fully in Phase 6 | ✅ |
| 0.6 | Create root `package.json` + `.npmrc` (pnpm workspace config) | ✅ |
| 0.7 | `uv venv --python 3.12` + `uv pip install -e ".[dev]"` — 153 packages installed | ✅ |

---

## Phase 1 — Data Modeling & Synthetic Assets *(~1 hr)*

**Goal:** All Python schemas defined; synthetic test data generated before any real code runs.

| Step | File | Notes | Status |
|------|------|-------|--------|
| 1.1 | `backend/app/schemas/pda.py` | Pydantic v2 `PDASchema` with `CostItem`, `CategoryEnum`, validator asserting `total_estimated == sum(estimated_items[*].estimated_value)` | ⬜ |
| 1.2 | `backend/app/schemas/fda.py` | `FDASchema` with nested `BoundingBox`, `ExtractedCostItem`. `confidence_score` field-validated to `[0.0, 1.0]`. Full schema exportable via `model_json_schema()` for LLM prompt injection | ⬜ |
| 1.3 | `backend/app/schemas/deviation.py` | `DeviationReport`, `DeviationLineItem`, `FlagReasonEnum` | ⬜ |
| 1.4 | `test_data/generate_fixtures.py` | Uses `reportlab` to produce `fda_pdfs/fda_001.pdf`–`fda_005.pdf` (mix of clean text, low-contrast, cursive overlay). Produces `pda_001.json`–`pda_005.json`. Intentional anomalies: one over-billing (+25%), one missing line item, one low-confidence `<0.85` extraction | ⬜ |

---

## Phase 2 — Backend API & AI Engine *(~3 hrs)*

**Goal:** Working FastAPI app that accepts an FDA PDF, extracts it with Claude, and stores results.

### 2.1 — SQLAlchemy Models & Alembic

- File: `backend/app/models/` — four models: `PortCall`, `DisbursementAccount` (status ENUM column), `CostItem` (JSONB for `bounding_box`), `AuditLog`
- Alembic configured via `alembic.ini` + `env.py` pointing to `DATABASE_URL` from settings
- Run `alembic revision --autogenerate -m "initial"` to produce migration

| Step | Status |
|------|--------|
| 2.1 SQLAlchemy Models + Alembic init | ⬜ |
| 2.2 FastAPI app bootstrap + health route | ⬜ |
| 2.3 Upload endpoint `POST /api/v1/da/upload` | ⬜ |
| 2.4 Docling + Claude extraction service | ⬜ |
| 2.5 Celery worker task | ⬜ |
| 2.6 Deviation engine | ⬜ |

---

## Phase 3 — Workflow State Machine *(~1 hr)*

**Goal:** Every DA state transition is validated, logged, and queryable via API.

| Step | Detail | Status |
|------|--------|--------|
| 3.1 | `DAStateMachine` class with `VALID_TRANSITIONS` dict | ⬜ |
| 3.2 | State enum: `UPLOADING → AI_PROCESSING → PENDING_ACCOUNTANT_REVIEW → PENDING_OPERATOR_APPROVAL → APPROVED → REJECTED → PUSHED_TO_ERP` | ⬜ |
| 3.3 | `GET /api/v1/da/{da_id}/status` | ⬜ |
| 3.4 | `PUT /api/v1/da/{da_id}/submit-to-operator` | ⬜ |
| 3.5 | `POST /api/v1/da/{da_id}/approve` + webhook fire | ⬜ |

---

## Phase 4 — Accountant React App *(~2.5 hrs)*

**Goal:** Split-screen PDF + form UI with live citation highlighting.

**Setup:** `pnpm create vite frontend-accountant --template react-ts` inside workspace, then add: `react-pdf`, `zustand`, `@tanstack/react-query`, `axios`, `tailwindcss`

| Step | Component / File | Status |
|------|-----------------|--------|
| 4.1 | `src/store/daStore.ts` — Zustand store | ⬜ |
| 4.2 | `src/api/daApi.ts` — react-query hooks | ⬜ |
| 4.3 | `src/components/PDFViewer.tsx` — PDF + Canvas overlay | ⬜ |
| 4.4 | `src/components/ItemForm.tsx` — editable cost item form | ⬜ |
| 4.5 | `src/components/FlagBadge.tsx` | ⬜ |
| 4.6 | `src/components/SubmitButton.tsx` | ⬜ |
| 4.7 | `src/pages/ReviewPage.tsx` — 50/50 split layout | ⬜ |

---

## Phase 5 — Operator React App *(~1.5 hrs)*

**Goal:** Clean approval dashboard.

**Setup:** `pnpm create vite frontend-operator --template react-ts` inside workspace, same dep set

| Step | Component | Status |
|------|-----------|--------|
| 5.1 | `src/components/DeviationTable.tsx` | ⬜ |
| 5.2 | `src/components/SummaryBar.tsx` | ⬜ |
| 5.3 | `src/components/JustificationInput.tsx` | ⬜ |
| 5.4 | `src/components/PDFModal.tsx` | ⬜ |
| 5.5 | `src/components/ApproveButton.tsx` | ⬜ |
| 5.6 | `src/pages/OperatorPage.tsx` | ⬜ |

> **Shared package:** `PDFViewer` and `BoundingBox` TypeScript type extracted to `packages/ui/` in the pnpm workspace to avoid duplication.

---

## Phase 6 — Packaging & Launch Assets *(~1 hr)*

| Step | Deliverable | Status |
|------|-------------|--------|
| 6.1 | `docker-compose.yml` — all 6 services with health checks | ⬜ |
| 6.2 | `backend/Dockerfile` — UV-based multi-stage build | ⬜ |
| 6.3 | `frontend-*/Dockerfile` — pnpm + Vite build → Nginx Alpine | ⬜ |
| 6.4 | `README.md` — Mermaid flow diagram + quickstart + ERP webhook guide | ⬜ |
| 6.5 | `.github/workflows/ci.yml` — ruff, mypy, pytest, pnpm lint/typecheck | ⬜ |
| 6.6 | MIT `LICENSE` | ⬜ |

---

## Build Order & Key Dependencies

```
Phase 0 (scaffold)
  └─ Phase 1 (schemas + test data)
       └─ Phase 2 (backend API + AI engine)  ← needs schemas
            ├─ Phase 3 (state machine)        ← needs DB models
            ├─ Phase 4 (accountant UI)        ← needs /upload + /status endpoints
            └─ Phase 5 (operator UI)          ← needs /submit-to-operator + /approve
                 └─ Phase 6 (Docker + docs)
```

---

## Open Assumptions

1. **Docling bounding boxes:** Output in **points** relative to page top-left. PDF.js (react-pdf) renders in CSS pixels. Conversion: `px = (pt / 72) * DPI` derived from the rendered `<Page>` `width` prop.
2. **Webhook debug endpoint:** `POST /api/v1/da/webhook-echo` included in backend to receive and log the final payload locally during development.
3. **Celery/Redis in dev:** `docker compose up redis` is the only dependency needed to run the worker locally outside Docker.
