# ClaimLens AI

Local Milestone 1 MVP for policy PDF validation, extraction, deterministic clause segmentation,
transactional persistence, and page/offset traceability. Milestone 1 uses FastAPI, SQLite,
SQLAlchemy, PyMuPDF, Pydantic, and Streamlit. Semantic retrieval, claims assessment, and Ollama
integration are reserved for Milestone 2.

## Windows one-command startup

Docker Desktop must be running. From PowerShell:

```powershell
cd claimlens-ai
Copy-Item .env.example .env
docker compose up --build
```

- Streamlit UI: http://localhost:8501
- OpenAPI: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

Docker starts the API and web UI. The host project `data` directory is mounted into the API,
so SQLite and uploaded PDFs remain available outside the containers.

Stop with `docker compose down`. To rebuild after source changes:

```powershell
docker compose up --build --force-recreate api web
```

## Persistent storage

All application records are stored in `data/claimlens.db`:

- policies and policy versions
- source documents and SHA-256 fingerprints
- source pages
- extracted clauses and offsets
- ingestion runs

Uploaded PDFs are stored below `data/uploads`. Docker uses the host `data` directory through a
bind mount rather than a disposable Docker volume.

## Local development

```powershell
py -3.13 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -e backend -e . pytest pytest-cov httpx
uvicorn app.main:app --app-dir backend --reload
cd frontend
streamlit run app/app.py
```

The local API resolves the SQLite database and upload directory to the project `data`
directory, independent of the current working directory.

## API ingestion

`POST /api/v1/documents/ingest` accepts multipart fields `file`, `carrier`, `policy_number`,
`product_name`, `effective_date`, `expiry_date`, optional `jurisdiction`,
`policy_holder`, `version_label`, and `source_metadata`.

The remaining routes expose documents, source pages, ordered clauses, and policy version history:

- `GET /api/v1/documents/{id}`
- `GET /api/v1/documents/{id}/pages`
- `GET /api/v1/documents/{id}/clauses`
- `GET /api/v1/policies/{id}/versions`
- `POST /api/v1/policies`
- `POST /api/v1/policies/{policy_id}/versions`

## Example upload

A text-based sample policy is included at
`evaluation/home-insurance-policy-example.pdf`. Example PowerShell upload:

```powershell
$pdf = "evaluation/home-insurance-policy-example.pdf"
curl.exe -F "file=@$pdf" `
  -F "carrier=carrier_policy" `
  -F "policy_number=00001" `
  -F "product_name=jeevan_bima_schema" `
  -F "jurisdiction=Kolkata" `
  -F "policy_holder=Suman_test" `
  -F "effective_date=2026-01-01" `
  -F "expiry_date=2026-12-31" `
  -F "version_label=1.0" `
  http://localhost:8000/api/v1/documents/ingest
```

The sample has successfully ingested as 1 page and 7 clauses in a verified local run.

## Configuration

See `.env.example`. Defaults enforce a 25 MB upload, 100 pages, and a local SQLite database.
The 25 MB upload and 100-page limits are configurable. Ollama is an optional Milestone 2
profile and is not started by default.

## Tests

```powershell
pytest -q
docker compose config
```

## Database migration

When upgrading an existing SQLite database, application startup automatically adds a missing
`clauses.clause_type` column. Ingestion failures are transactional, so policy and document
metadata is not committed unless clause persistence succeeds.
