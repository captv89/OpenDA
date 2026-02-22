**OpenDA**

AI Disbursement Account Analyzer

Full Project Specification & Claude Code Build Guide

+--------+-----------:+--------------+
|        | Version    | **1.0.0 --   |
|        |            | Open         |
|        | Domain     | Source**     |
|        |            |              |
|        | License    | **Maritime   |
|        |            | Port         |
|        |            | Agency**     |
|        |            |              |
|        |            | **MIT**      |
+--------+------------+--------------+

**1. Executive Summary**

OpenDA is an open-source, Human-in-the-Loop AI platform built to
automate the validation of Final Disbursement Accounts (FDA) in the
maritime port agency industry. It compares AI-extracted data from messy
FDA PDFs against structured Proforma DA (PDA) estimates, flags
anomalies, routes them through an Accountant review, and then pushes a
finalized, auditable JSON payload to an ERP or VMS via webhook.

The project is designed to be built entirely using Claude Code, with
each phase mapped to discrete, independently executable modules. This
document serves as the definitive specification for Claude Code to
generate each module with zero ambiguity.

+-----------------------------------------------------------------------+
| **The Core Problem**                                                  |
|                                                                       |
| Port agents worldwide process hundreds of FDAs per month --- each a   |
| collection of scanned receipts, handwritten chits, and digital        |
| invoices. Manually reconciling these against PDA estimates is slow,   |
| error-prone, and scales poorly. OpenDA eliminates 80%+ of manual data |
| entry while keeping a human accountant in control of final accuracy.  |
+-----------------------------------------------------------------------+

**2. System Architecture Overview**

OpenDA is structured as a decoupled three-tier system. The backend is a
Python/FastAPI REST API service responsible for all AI orchestration,
document processing, and business logic. The frontend consists of two
distinct React applications --- one for the Port DA Accountant and one
for the Commercial Operator. PostgreSQL serves as the single source of
truth for DA state, and Redis handles background job queuing for
long-running AI extraction tasks.

  --------------------------------------------------------------------------
  **Layer**          **Technology**              **Responsibility**
  ------------------ --------------------------- ---------------------------
  Backend API        Python 3.12 + FastAPI       AI orchestration, state
                                                 machine, webhook

  Document AI        IBM Docling + Claude        PDF parsing, OCR,
                     claude-sonnet-4-6           structured extraction

  Database           PostgreSQL 16 + SQLAlchemy  DA state, JSON schemas,
                                                 audit trail

  Job Queue          Redis + Celery              Async PDF processing

  Frontend --        React 18 + Vite + Tailwind  Split-screen PDF validation
  Accountant         CSS                         UI

  Frontend --        React 18 + Vite + Tailwind  Commercial deviation
  Operator           CSS                         approval dashboard

  PDF Viewer         react-pdf (PDF.js)          Bounding-box citation
                                                 rendering

  Containerization   Docker + docker-compose     Single-command local and
                                                 cloud spin-up
  --------------------------------------------------------------------------

**3. Full Technology Stack & Rationale**

**3.1 IBM Docling --- PDF Ingestion Engine**

Docling (github.com/DS4SD/docling) is IBM Research\'s open-source
document understanding library. It is the highest-quality
PDF-to-structured-data tool available in Python as of 2025. It natively
handles scanned documents via integrated OCR (EasyOCR/Tesseract),
produces bounding-box coordinates for every extracted element,
reconstructs table structures from scanned images, and outputs a rich
DoclingDocument object that can be serialized to JSON, Markdown, or
HTML. This makes it ideal for FDA processing where documents range from
clean digital invoices to handwritten chits.

+-----------------------------------------------------------------------+
| **Why Docling over PyMuPDF or pdfplumber?**                           |
|                                                                       |
| - Docling uses layout-aware ML models, not heuristic regex ---        |
|   critical for messy maritime receipts                                |
|                                                                       |
| - Native bounding-box output per text element is required for the     |
|   citation-click UI feature                                           |
|                                                                       |
| - Table reconstruction from scanned images outperforms all Python     |
|   alternatives                                                        |
|                                                                       |
| - IBM Research backing ensures long-term maintenance for an           |
|   open-source project                                                 |
+-----------------------------------------------------------------------+

**3.2 Anthropic Claude claude-sonnet-4-6 --- LLM Extraction Engine**

Claude claude-sonnet-4-6 via the Anthropic API is used for the
structured data extraction step. After Docling converts the FDA PDF into
a rich text/JSON representation, Claude is prompted with a strict JSON
schema and instructed to extract each cost line item with a
confidence_score. Claude\'s 200K token context window handles even the
largest multi-invoice FDA packages in a single API call.

**3.3 FastAPI --- Backend Framework**

FastAPI provides automatic OpenAPI documentation, Pydantic v2 data
validation, and native async support --- essential for non-blocking LLM
API calls. It is the de facto standard for Python AI-backend services in
2025.

**3.4 React 18 + Vite + Tailwind CSS --- Frontend**

React 18 is chosen over Svelte for its mature ecosystem, specifically
the availability of react-pdf (PDF.js wrapper) which is the only
production-ready library for rendering PDFs with programmatic
scroll-to-bounding-box functionality. Vite provides sub-second HMR for
fast Claude Code iteration cycles. Tailwind CSS eliminates custom CSS
overhead.

**3.5 PostgreSQL + SQLAlchemy (Async) --- Database**

PostgreSQL\'s JSONB column type stores the PDA and FDA schemas natively
with indexing support. The async SQLAlchemy driver (asyncpg) prevents
database calls from blocking the FastAPI event loop during AI
processing.

**3.6 Celery + Redis --- Async Job Queue**

PDF processing and LLM extraction can take 15--60 seconds per document.
Celery workers handle these jobs asynchronously, with Redis as the
message broker. The FastAPI endpoint immediately returns a job_id; the
frontend polls for status.

**3.7 Complete Dependency List**

  ----------------------------------------------------------------------------------
  **Package**             **Version**     **Layer**     **Purpose**
  ----------------------- --------------- ------------- ----------------------------
  docling                 \^2.x           Backend       PDF parsing, OCR, bounding
                                                        boxes

  anthropic               \^0.29          Backend       Claude claude-sonnet-4-6 LLM
                                                        API

  fastapi                 \^0.111         Backend       REST API framework

  pydantic                \^2.7           Backend       Schema validation

  sqlalchemy\[asyncio\]   \^2.0           Backend       Async ORM

  asyncpg                 \^0.29          Backend       PostgreSQL async driver

  celery\[redis\]         \^5.4           Backend       Async job queue

  alembic                 \^1.13          Backend       DB migrations

  httpx                   \^0.27          Backend       Async HTTP client (webhooks)

  react                   18.x            Frontend      UI framework

  react-pdf               \^7.x           Frontend      PDF rendering with bounding
                                                        boxes

  zustand                 \^4.x           Frontend      Lightweight state management

  react-query             \^5.x           Frontend      Server state / polling

  tailwindcss             \^3.x           Frontend      Utility-first CSS

  vite                    \^5.x           Frontend      Build tool / dev server
  ----------------------------------------------------------------------------------

**4. Data Schemas**

**4.1 PDA JSON Schema (Baseline Estimate)**

This schema defines the Proforma DA --- the port agent\'s upfront cost
estimate sent to the ship operator before the vessel arrives. It is the
baseline against which the FDA will be compared.

+-----------------------------------------------------------------------+
| **PDA Schema --- Key Fields**                                         |
|                                                                       |
| - port_call_id: string --- Unique identifier for the port call (e.g., |
|   \'PC-2025-SGSIN-0042\')                                             |
|                                                                       |
| - vessel_name: string --- Full vessel name                            |
|                                                                       |
| - vessel_imo: string --- IMO number for deduplication                 |
|                                                                       |
| - port_code: string --- UN/LOCODE (e.g., \'SGSIN\')                   |
|                                                                       |
| - currency: string --- ISO 4217 (e.g., \'USD\', \'SGD\')              |
|                                                                       |
| - estimated_items: array of CostItem objects                          |
|                                                                       |
| <!-- -->                                                              |
|                                                                       |
| - category: enum (PILOTAGE \| TOWAGE \| PORT_DUES \| AGENCY_FEE \|    |
|   LAUNCH_HIRE \| WASTE_DISPOSAL \| OTHER)                             |
|                                                                       |
| - description: string --- Free text description                       |
|                                                                       |
| - estimated_value: number --- Numeric amount                          |
|                                                                       |
| - unit: string --- e.g., \'per_movement\', \'per_hour\', \'lump_sum\' |
|                                                                       |
| <!-- -->                                                              |
|                                                                       |
| - total_estimated: number --- Sum of all estimated_items              |
|                                                                       |
| - valid_until: ISO 8601 date string                                   |
+-----------------------------------------------------------------------+

**4.2 FDA JSON Schema (AI Extraction Output)**

This is the schema that Claude claude-sonnet-4-6 must output. Every
field includes a confidence_score and a pdf_citation_bounding_box ---
the coordinates used by the frontend to draw a highlight rectangle over
the source document. This schema is injected into the LLM system prompt
as a required output contract.

+-----------------------------------------------------------------------+
| **FDA Schema --- Key Fields (AI Output)**                             |
|                                                                       |
| - port_call_id: string --- Must match the PDA                         |
|                                                                       |
| - processing_job_id: string --- Celery job ID for traceability        |
|                                                                       |
| - extraction_model: string --- e.g., \'claude-sonnet-4-6-20250514\'   |
|                                                                       |
| - extracted_items: array of ExtractedCostItem objects                 |
|                                                                       |
| <!-- -->                                                              |
|                                                                       |
| - category: enum --- Same categories as PDA                           |
|                                                                       |
| - description: string                                                 |
|                                                                       |
| - actual_value: number                                                |
|                                                                       |
| - currency: string                                                    |
|                                                                       |
| - confidence_score: float \[0.0 -- 1.0\]                              |
|                                                                       |
| - pdf_citation_bounding_box: { page: int, x1: float, y1: float, x2:   |
|   float, y2: float }                                                  |
|                                                                       |
| - supporting_document_type: enum (DIGITAL_INVOICE \| SCANNED_RECEIPT  |
|   \| HANDWRITTEN_CHIT \| OFFICIAL_RECEIPT)                            |
|                                                                       |
| <!-- -->                                                              |
|                                                                       |
| - items_not_found: array of strings --- PDA categories with no        |
|   matching FDA evidence                                               |
|                                                                       |
| - total_actual: number                                                |
+-----------------------------------------------------------------------+

**5. Phase-by-Phase Build Plan for Claude Code**

**Phase 1 --- Data Modeling & Synthetic Assets**

**Claude Code Prompt:** \"Generate the following files in the /schemas
and /test_data directories.\"

**Task 1.1 --- Define PDA Pydantic Schema**

- File: backend/app/schemas/pda.py

- Use Pydantic v2 BaseModel with strict field types and JSON
  serialization

- Include all fields defined in Section 4.1

- Add a validator ensuring total_estimated equals the sum of
  estimated_items

**Task 1.2 --- Define FDA Pydantic Schema**

- File: backend/app/schemas/fda.py

- Model the ExtractedCostItem with BoundingBox as a nested Pydantic
  model

- Confidence score must be validated to range \[0.0, 1.0\] using
  field_validator

- The entire schema must be serializable to JSON for injection into
  Claude\'s system prompt

**Task 1.3 --- Generate Synthetic Test Data**

- File: test_data/generate_fixtures.py

- Generate 5 PDA JSON files (pda_001.json through pda_005.json)

- Generate corresponding FDA PDFs using reportlab: mix digital invoices
  (clean text), scanned-style receipts (rotated, low-contrast), and
  handwritten-style chits (cursive font overlay)

- Include deliberate discrepancies: one over-billing, one missing item,
  one low-confidence extraction scenario

**Phase 2 --- AI Engine & Backend**

**Claude Code Prompt:** \"Build the FastAPI backend in /backend with the
following structure and logic.\"

**Task 2.1 --- Backend Repository Setup**

- Directory: backend/

- Files: main.py, app/api/routes/, app/models/, app/schemas/,
  app/services/, app/workers/

- Database: PostgreSQL with the following tables --- port_calls,
  disbursement_accounts, cost_items, audit_log

- Migrations: Alembic with auto-generation from SQLAlchemy models

- Config: Pydantic Settings class reading from .env file

**Task 2.2 --- PDF Ingestion Endpoint**

- Endpoint: POST /api/v1/da/upload

- Accepts: multipart/form-data with port_call_id (string) + fda_pdf
  (file)

- Action: Validates file type, stores PDF to /uploads/{port_call_id}/,
  creates DA record in DB with status=UPLOADING, enqueues a Celery task,
  returns { job_id, da_id, status }

- Docling pipeline: DoclingDocument → export_to_dict() → pass structured
  content to LLM service

**Task 2.3 --- LLM Extraction Service**

- File: backend/app/services/extraction_service.py

- System prompt injects the full FDA Pydantic schema as a JSON schema
  string

- User prompt provides the Docling output as a structured text block

- Claude is instructed via tool_use / structured output to return only
  valid FDA JSON

- Retry logic: 3 attempts with exponential backoff on API errors

- After extraction, update DA status to PENDING_REVIEW

**Task 2.4 --- Deviation Engine**

- File: backend/app/services/deviation_engine.py

- Input: PDA JSON + FDA JSON for the same port_call_id

- Output: DeviationReport with per-line variance (absolute \$ and
  percentage), total_variance, items_not_billed, items_not_estimated

- Logic: Match items by category enum. If confidence_score \< 0.85 OR
  item missing from FDA → set flag=REQUIRES_REVIEW

**Phase 3 --- Workflow State Machine**

**Claude Code Prompt:** \"Implement the DA state machine as a service
class with transition validation.\"

**Task 3.1 --- DA State Tracking**

- States: UPLOADING → AI_PROCESSING → PENDING_ACCOUNTANT_REVIEW →
  PENDING_OPERATOR_APPROVAL → APPROVED → REJECTED → PUSHED_TO_ERP

- File: backend/app/services/state_machine.py

- Each transition logs to audit_log table with timestamp, actor (user_id
  or \'SYSTEM\'), and previous/new state

- Endpoint: GET /api/v1/da/{da_id}/status --- returns current state,
  flagged items count, timestamps

**Task 3.2 --- Auto-Flagging Logic**

- After extraction, iterate all ExtractedCostItems

- Flag as REQUIRES_REVIEW if: confidence_score \< 0.85, category has no
  matching PDA line, absolute deviation \> \$500 or percentage deviation
  \> 10%

- Flagged items stored in DB with a flag_reason enum: LOW_CONFIDENCE \|
  MISSING_PDA_LINE \| HIGH_DEVIATION

**Phase 4 --- Accountant UI**

**Claude Code Prompt:** \"Build the Accountant frontend React app in
/frontend-accountant with the following components.\"

**Task 4.1 --- Frontend Repository Setup**

- Directory: frontend-accountant/

- Vite + React 18 + TypeScript + Tailwind CSS

- State: Zustand store for selectedFieldId (drives PDF highlight) and
  formState

- API Layer: react-query with axios, polling /api/v1/da/{da_id}/status
  until status !== AI_PROCESSING

**Task 4.2 --- Split-Screen Interface**

- Layout: Two-column flex container (50/50 split with a draggable
  divider)

- Left Pane: react-pdf \<Document\> + \<Page\> renderer. Renders the FDA
  PDF at the correct page.

- Right Pane: Dynamic form generated from the FDA JSON --- one form
  section per cost category

- Flagged items rendered with a red left-border and a warning icon with
  the flag_reason

**Task 4.3 --- Citation & Correction Logic**

- On field focus (right pane): dispatch to Zustand store → left pane
  scrolls to the correct PDF page and draws a yellow semi-transparent
  rectangle over the bounding box coordinates

- Bounding box rendering: Canvas overlay on top of the react-pdf Page
  component

- Editable fields: All actual_value and description fields are editable
  inputs. Edits set a dirty flag and update the Zustand store.

- \'Override\' button on low-confidence items: allows Accountant to
  confirm an AI value is correct, removing the flag

**Task 4.4 --- Submit to Operator Action**

- Validation: All REQUIRES_REVIEW items must be either edited or marked
  as confirmed before submission

- Action: PUT /api/v1/da/{da_id}/submit-to-operator with the corrected
  FDA JSON payload

- Backend transitions state to PENDING_OPERATOR_APPROVAL and records the
  accountant\'s user_id

**Phase 5 --- Operator UI**

**Claude Code Prompt:** \"Build the Operator frontend React app in
/frontend-operator with the following components.\"

**Task 5.1 --- Operator Dashboard**

- Directory: frontend-operator/

- Main view: A clean data table with columns: Cost Category \| PDA
  Estimate \| FDA Actual (Verified) \| Deviation (\$) \| Deviation (%)
  \| Status

- PDF is hidden by default; a \'View Source Documents\' button opens a
  modal with the full PDF

- Summary bar at the top: Total PDA \| Total FDA \| Net Variance \|
  Variance %

**Task 5.2 --- Deviation Highlighting & Comments**

- Rows with deviation \> 10% or \> \$500: highlighted in amber
  background

- Each highlighted row shows an expandable \'Justification\' text area

- Operator must enter a justification comment before approving any row
  with a flag

- Overall remarks text area at the bottom of the page for general
  approval notes

**Task 5.3 --- Final Approval & Webhook**

- \'Approve\' button: disabled until all flagged rows have justification
  comments

- Action: POST /api/v1/da/{da_id}/approve with { operator_remarks,
  item_justifications }

- Backend: transitions state to APPROVED, generates the final canonical
  JSON package, fires the webhook

- Webhook payload: Full PDA + verified FDA + DeviationReport + approval
  metadata + audit trail as a single JSON object

**Phase 6 --- Packaging & Launch**

**Claude Code Prompt:** \"Generate the Docker, documentation, and launch
assets.\"

**Task 6.1 --- Docker Compose**

- Services: postgres, redis, backend (FastAPI), celery-worker,
  frontend-accountant (Nginx), frontend-operator (Nginx)

- Environment variables via .env.example file --- ANTHROPIC_API_KEY,
  DATABASE_URL, REDIS_URL, WEBHOOK_URL

- Health checks on all services. backend depends_on postgres and redis
  with condition: service_healthy

**Task 6.2 --- README.md**

- Explain the two-stage Human-in-the-Loop workflow with a Mermaid flow
  diagram

- Quickstart: git clone → cp .env.example .env → docker-compose up

- \'Connecting to your ERP\' section: explain how to replace the dummy
  webhook endpoint

- Architecture diagram and annotated screenshots of both UIs

**Task 6.3 --- Launch Assets**

- GitHub repository with MIT license, GitHub Actions CI for linting and
  tests

- LinkedIn article draft: title \'Why AI Alone Cannot Sign a
  Disbursement Account --- OpenDA\'s Human-in-the-Loop Architecture\'

- HackerNews Show HN post draft

**6. Claude Code Prompting Guide**

The following prompts are optimized for use with Claude Code CLI. Each
prompt is scoped to a single module to prevent context overflow and
ensure deterministic output.

**6.1 Backend Bootstrap**

+-----------------------------------------------------------------------+
| **Claude Code Prompt --- Phase 2, Task 2.1**                          |
|                                                                       |
| Create a FastAPI backend project in ./backend/ with the following     |
| structure:                                                            |
|                                                                       |
| - Python 3.12, FastAPI 0.111, SQLAlchemy 2.0 async, asyncpg, Alembic, |
|   Celery 5.4, Redis                                                   |
|                                                                       |
| - Database: PostgreSQL. Create SQLAlchemy models for: PortCall,       |
|   DisbursementAccount (with status enum), CostItem (with              |
|   confidence_score, bounding_box JSONB, flag_reason enum), AuditLog   |
|                                                                       |
| - Pydantic Settings class reading ANTHROPIC_API_KEY, DATABASE_URL,    |
|   REDIS_URL from .env                                                 |
|                                                                       |
| - Alembic config pointing to the SQLAlchemy models. Run alembic       |
|   revision \--autogenerate                                            |
|                                                                       |
| - Create a /api/v1/health endpoint returning { status: ok, db:        |
|   connected, redis: connected }                                       |
|                                                                       |
| - All async. Use lifespan context manager for startup/shutdown DB     |
|   connection pooling                                                  |
+-----------------------------------------------------------------------+

**6.2 Docling + LLM Extraction**

+-----------------------------------------------------------------------+
| **Claude Code Prompt --- Phase 2, Tasks 2.2 & 2.3**                   |
|                                                                       |
| In ./backend/app/services/extraction_service.py, create an            |
| ExtractionService class:                                              |
|                                                                       |
| - Method: async def process_pdf(self, pdf_path: str, pda: PDASchema)  |
|   -\> FDASchema                                                       |
|                                                                       |
| - Step 1: Use docling.DocumentConverter to convert the PDF. Export to |
|   dict. Extract all TextItem bounding boxes.                          |
|                                                                       |
| - Step 2: Build a system prompt that includes: (a) the FDA Pydantic   |
|   schema serialized as JSON Schema, (b) instruction to return ONLY    |
|   valid JSON matching the schema, (c) instruction to assign           |
|   confidence_score based on document clarity and value unambiguity    |
|                                                                       |
| - Step 3: Call anthropic.AsyncAnthropic().messages.create with        |
|   model=\'claude-sonnet-4-6-20250514\', the system prompt, and the    |
|   Docling output as user message                                      |
|                                                                       |
| - Step 4: Parse the response, validate against FDASchema, return      |
|                                                                       |
| - Wrap in a Celery task in app/workers/tasks.py                       |
+-----------------------------------------------------------------------+

**6.3 Accountant UI --- PDF Citation Component**

+-----------------------------------------------------------------------+
| **Claude Code Prompt --- Phase 4, Task 4.3**                          |
|                                                                       |
| In ./frontend-accountant/src/components/PDFViewer.tsx, build a PDF    |
| viewer component:                                                     |
|                                                                       |
| - Use react-pdf Document and Page components to render the PDF        |
|                                                                       |
| - Accept a highlightBox prop: { page: number, x1: number, y1: number, |
|   x2: number, y2: number } \| null                                    |
|                                                                       |
| - When highlightBox is set, scroll to the correct page and render a   |
|   Canvas overlay on top of the Page component drawing a               |
|   semi-transparent yellow rectangle at the bounding box coordinates   |
|                                                                       |
| - Bounding box coordinates from Docling are in points (1/72 inch).    |
|   Convert to pixel coordinates using the PDF page\'s rendered pixel   |
|   dimensions.                                                         |
|                                                                       |
| - Smooth scroll animation when switching between pages                |
|                                                                       |
| - Export: default export PDFViewer                                    |
+-----------------------------------------------------------------------+

**7. Repository Folder Structure**

+-----------------------------------------------------------------------+
| **Monorepo Structure**                                                |
|                                                                       |
| **openda/**                                                           |
|                                                                       |
| **├── backend/**                                                      |
|                                                                       |
| │ ├── app/                                                            |
|                                                                       |
| │ │ ├── api/routes/ \# FastAPI routers                                |
|                                                                       |
| │ │ ├── models/ \# SQLAlchemy models                                  |
|                                                                       |
| │ │ ├── schemas/ \# Pydantic schemas (pda.py, fda.py, deviation.py)   |
|                                                                       |
| │ │ ├── services/ \# extraction_service.py, deviation_engine.py,      |
| state_machine.py                                                      |
|                                                                       |
| │ │ └── workers/ \# Celery tasks                                      |
|                                                                       |
| │ ├── alembic/                                                        |
|                                                                       |
| │ ├── tests/                                                          |
|                                                                       |
| │ └── pyproject.toml                                                  |
|                                                                       |
| ├── frontend-accountant/ \# React app for Port DA Accountant          |
|                                                                       |
| │ ├── src/components/ \# PDFViewer, ItemForm, FlagBadge, SubmitButton |
|                                                                       |
| │ └── src/store/ \# Zustand stores                                    |
|                                                                       |
| ├── frontend-operator/ \# React app for Commercial Operator           |
|                                                                       |
| │ └── src/components/ \# DeviationTable, JustificationInput,          |
| ApproveButton                                                         |
|                                                                       |
| ├── test_data/                                                        |
|                                                                       |
| │ ├── pda_001.json \... pda_005.json                                  |
|                                                                       |
| │ └── fda_pdfs/ \# Synthetic FDA PDFs                                 |
|                                                                       |
| ├── schemas/ \# JSON Schema exports for documentation                 |
|                                                                       |
| ├── docker-compose.yml                                                |
|                                                                       |
| ├── .env.example                                                      |
|                                                                       |
| └── README.md                                                         |
+-----------------------------------------------------------------------+
