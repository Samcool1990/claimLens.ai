# ClaimLens AI Implementation Plan

**Status:** Approved for scaffold handoff
**Created:** 2026-11-01
**Mode:** Local Docker MVP

## 1. Project Overview

- **Product:** ClaimLens AI
- **Goal:** Implement and validate the structured PDF ingestion pipeline for insurance policies without adding Azure dependencies.
- **Milestone 1 scope:** PDF validation, PyMuPDF text extraction, deterministic clause segmentation, SHA-256 fingerprinting, transactional SQLite persistence, and page/offset traceability.
- **Deferred to Milestone 2:** semantic retrieval, embeddings, vector search, Ollama-based policy assessment, claim explanation, and answer citation generation.
- **Runtime:** Python 3.13, FastAPI, SQLAlchemy 2.x, Pydantic v2, Streamlit, PyMuPDF, pytest, Docker Compose, and Ollama for the reserved Milestone 2 service boundary.
- **Success criteria:** a valid policy PDF can be uploaded through Streamlit or FastAPI, committed atomically with one policy document/version and all clauses, then traced back to source page and character offsets.

### Clarifications to resolve before or during scaffolding

1. **Repository structure override:** no user-provided tree exists. The implementation will use a conventional monorepository layout unless a repository tree is supplied; this is not an Azure layout.
2. **Policy metadata fields:** include `carrier`, `policy_number`, `product_name`, optional `jurisdiction`, optional policy-holder identifier, `effective_date`, `expiry_date`, version label, and source metadata. Final field nullability should remain flexible until representative policy fixtures are provided.
3. **Clause segmentation:** begin with deterministic heading, numbering, and blank-line boundaries. Preserve source page and character offsets. Avoid NLP/LLM semantics in Milestone 1.
4. **Upload limits:** default to 25 MB, 100 pages, MIME and magic-number validation, configurable through environment variables. Enforce the limits consistently at API and Streamlit boundaries.
5. **Duplicate behavior:** compute SHA-256 before parsing and return the existing document when the same policy file is uploaded, unless a caller explicitly requests a new document/version.

## 2. Target Architecture

- `frontend/`: Streamlit interface for upload, validation feedback, persisted-document review, and clause/page traceability.
- `backend/`: FastAPI application with versioned REST API, schemas, database models, repository/service modules, PDF parsing, segmentation, and transaction management.
- `ollama/`: reserved configuration and Docker Compose service for Milestone 2; Milestone 1 code must not call it and must be deployable and testable without semantic retrieval.
- `tests/`: unit, integration, database transaction, fixture, API, and segmentation tests.
- `data/`: SQLite volume and runtime-only PDFs; source fixture PDFs are kept under `tests/fixtures/`.
- `docs/`: API usage, ingestion contract, data model, and development notes.

Runtime paths remain behind interface abstractions. No Azure SDK, Azure resource deployment, managed identity, Blob Storage, or Azure database is introduced.

## 3. Implementation Plan

### Backend foundations

1. Create the FastAPI application factory, settings, health route, dependency injection, and error handlers.
2. Add SQLAlchemy 2.x declarative entities and typed sessions for policy metadata, policy versions, documents, document pages, and clauses.
3. Initialize the SQLite schema at application startup through a migration bootstrap suited to this local MVP; support disposable test databases.
4. Add Pydantic v2 commands and response models for upload validation and persisted ingestion results.

### PDF ingestion

1. Stream the multipart upload without loading unbounded input in memory.
2. Validate extension, MIME declaration, PDF signature, size, page count, encryption, and basic structural readability.
3. Calculate SHA-256 before extraction.
4. Extract ordered page text with PyMuPDF, including page numbers and per-page character ranges.
5. Detect duplicate documents by fingerprint. For non-duplicates, persist document/page metadata and clause records.
6. Commit policy metadata, version, document, pages, and clauses in one SQLAlchemy transaction; roll back all writes on extraction, segmentation, persistence, or validation failure.
7. Record deterministic clause start/end offsets and source page references.

### Streamlit

1. Provide PDF selection and validation feedback.
2. Call FastAPI ingestion endpoints rather than accessing SQLAlchemy directly.
3. Show document fingerprint, policy metadata, version, processing state, clause text, source page, and offsets.
4. Display safe validation and duplicate results.

### Containerization

1. Add separate FastAPI and Streamlit images built from Python 3.13.
2. Add Ollama as a local compose service with Milestone 2 configuration and no ingestion dependency.
3. Persist SQLite and runtime uploads in named volumes or fixed local paths.
4. Add healthchecks and service dependency ordering.

## 4. Technology Stack

| Layer | Technology | Milestone responsibility |
|---|---|---|
| API | Python 3.13, FastAPI | Upload validation and ingestion commands |
| UI | Streamlit | Local ingestion and traceability workflow |
| PDF | PyMuPDF | Signature/readability checks and page text extraction |
| Database | SQLite, SQLAlchemy 2.x | Transactional Milestone 1 persistence |
| Schemas | Pydantic v2 | Validated API contracts |
| Tests | pytest, pytest-cov, httpx | Unit, API, transaction, and fixture coverage |
| Runtime | Docker Compose | Local API, UI, SQLite, and Ollama services |
| Local model | Ollama | Reserved for Milestone 2; no Milestone 1 model call |

Dependency locks will be generated and committed. Development dependencies will remain separate from runtime dependencies.

## 5. Data Model

- **Policy:** logical policy grouping such as carrier, policy number, product name, jurisdiction, and optional holder identity.
- **PolicyVersion:** effective date, expiry date, version label/source, policy relationship, and audit timestamps.
- **Document:** original filename, media type, byte size, SHA-256, validation state, storage location, policy-version relationship, and timestamps.
- **DocumentPage:** document relationship, zero-based page index, one-based page number, extracted-text length, and content hash.
- **Clause:** document and policy-version relationships, normalized heading/number/title, clause text, page number, start/end character offsets, ordinal position, segmentation method, and timestamps.
- **IngestionRun (optional but recommended):** status, fingerprint, validation error, timing, and document relationship for auditability.

SQLite foreign keys and constraints are enabled. Unique constraints cover policy identity key, version identity, document fingerprint/deduplication, page positions, and clause ordinals. Add indexes for policy, version, fingerprint, and clause source relationships.

Transaction boundary:

`validate input -> extract/read pages -> segment clauses -> begin transaction -> persist policy/version/document/pages/clauses -> commit`

Only the committed success payload is returned. Extraction occurs before the database transaction; persistence and all dependent writes occur inside one transaction.

## 6. Design System & UI

**Component Library:** Streamlit built-in components with custom theme configuration

- Upload panel using `st.file_uploader`, MIME-aware validation, progress feedback, and clear rerun behavior.
- Status panel for accepted/rejected, duplicate, committed, and failed ingestion.
- Document table showing policy identity, version, SHA-256, pages, and ingestion timestamp.
- Clause explorer with selectable source page and complete traceability metadata.
- Error component using concise user-safe messages and no internal stack traces.
- Reserved navigation for Milestone 2 assessment features, disabled until semantic retrieval exists.

## 7. API Design

- `GET /api/v1/health`: API and database health.
- `POST /api/v1/policies/{policy_id}/versions/{version_id}/documents`: ingest an uploaded PDF transactionally.
- `POST /api/v1/documents/ingest`: validate metadata, create or resolve policy/version, and ingest in one API operation when policy IDs are not known.
- `GET /api/v1/documents/{document_id}`: document summary and ingestion status.
- `GET /api/v1/documents/{document_id}/pages`: page traceability records.
- `GET /api/v1/documents/{document_id}/clauses`: ordered clauses with page and offset traceability.
- `GET /api/v1/policies/{policy_id}/versions`: version history.

Exact route payloads and optional `policy-idempotency-key` behavior may be finalized in the Pydantic contract. Duplicate uploads return an existing-document reference and no duplicate write.

Milestone 2-only endpoints for embeddings, retrieval, and Ollama assessment must not be implemented in Milestone 1.

## 8. Security & Access

- MVP is local-only and uses Docker Compose networking, not public Azure services.
- Do not expose FastAPI, SQLite, or Ollama to untrusted networks without an explicit authentication and deployment design.
- Stream uploaded bytes directly through a bounded temporary file; enforce size, page-count, and extraction limits.
- Configure temporary storage and SQLite paths through environment variables.
- Rejected PDFs, validation errors, and database failures must not leak absolute paths, SQL statements, or secrets.
- Add filename sanitization and generated storage names.
- Store no API credentials or model secrets in source control.

Authentication is explicitly out of Milestone 1 scope. The documented MVP is not production multi-user software.

## 9. Testing Strategy

- Unit tests for SHA-256, filename/MIME/signature, size/page limits, encrypted PDFs, segmentation, offsets, and duplicate detection.
- Fixture PDFs cover scanned, heading-rich, numbered, line-wrapped, encrypted, malformed, oversized, and duplicate cases.
- Integration tests start FastAPI through `httpx`, using a disposable SQLite database.
- Transaction tests inject failures into page/clause persistence and prove all related writes roll back.
- Streamlit smoke tests verify upload and error rendering without coupling UI tests to SQLAlchemy.
- Container tests verify service startup, healthchecks, volume persistence, and API-to-SQLite connectivity.
- pytest coverage should target ingestion, validation, segmentation, and transaction logic.
- Ollama availability is not part of Milestone 1 startup or pytest health gates.

## 10. Deployment

- `compose.yaml` starts FastAPI, Streamlit, and optionally Ollama on a local bridge network.
- `api` waits for database initialization only; SQLite requires no separate server container.
- `web` depends on healthy `api`.
- Ollama uses an optional profile so Milestone 1 can run without pulling or starting a model.
- Bind SQLite and PDF runtime directories to named volumes with documented backup/restore commands.
- Ollama model configuration, model name, and prompts are reserved for Milestone 2.
- Environment variables cover database URL, upload limits, storage directory, API URL, and Ollama endpoint.
- No Azure resource provisioning or Azure credentials are required.

## 11. Repository Structure

Use the following layout unless the user supplies an overriding repository structure:

```text
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── db/
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── app/
│   ├── Dockerfile
│   └── pyproject.toml
├── tests/
│   ├── api/
│   ├── fixtures/
│   ├── integration/
│   └── unit/
├── data/
│   └── README.md
├── docs/
├── compose.yaml
├── .env.example
├── pyproject.toml
└── README.md
```
