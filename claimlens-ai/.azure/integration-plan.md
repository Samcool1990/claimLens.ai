# ClaimLens AI integration hand-off

- Backend folder: `claimlens-ai/backend`; command: `uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000`; port 8000; health: `/api/v1/health`.
- Frontend folder: `claimlens-ai/frontend`; build via Streamlit Docker image; dev: `streamlit run app/app.py`; API seam: API calls in `frontend/app/app.py` via API_URL; no mock files.
- API routes:
  - `GET /api/v1/health`
  - `POST /api/v1/documents/ingest`
  - `POST /api/v1/policies/{policy_id}/versions/{version_id}/documents`
  - `GET /api/v1/documents/{document_id}`
  - `GET /api/v1/documents/{document_id}/pages`
  - `GET /api/v1/documents/{document_id}/clauses`
  - `GET /api/v1/policies/{policy_id}/versions`
- Database: SQLite; SQLAlchemy startup bootstrap in `backend/app/db/session.py`; no migration tool; connection env `DATABASE_URL`. Explicitly create no seed data.
- Shared types: backend Pydantic schemas in `backend/app/schemas/ingestion.py`; frontend currently consumes JSON directly.
- Services: FastAPI ingestion Essential; Streamlit Essential; SQLite Essential; Ollama Enhancement on `milestone2` profile only.
