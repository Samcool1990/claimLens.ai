# ClaimLens AI

Local Milestone 1 MVP for policy PDF validation, extraction, deterministic clause segmentation,
transactional persistence, and page/offset traceability. There is no Azure deployment and no
Milestone 2 model call.

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

Stop with `docker compose down`. To remove the SQLite/upload volume, use
`docker compose down -v`.

## Local development

```powershell
py -3.13 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -e backend -e .
pip install pytest pytest-cov httpx
uvicorn app.main:app --app-dir backend --reload
cd frontend
streamlit run app/app.py
```

## API ingestion

`POST /api/v1/documents/ingest` accepts multipart fields `file`, `carrier`, `policy_number`,
`product_name`, `effective_date`, `expiry_date`, optional `jurisdiction`,
`policy_holder`, `version_label`, and `source_metadata`.

The remaining routes expose documents, source pages, ordered clauses, and policy version history:

- `GET /api/v1/documents/{id}`
- `GET /api/v1/documents/{id}/pages`
- `GET /api/v1/documents/{id}/clauses`
- `GET /api/v1/policies/{id}/versions`

## Configuration

See `.env.example`. Defaults enforce a 25 MB upload, 100 pages, and a local SQLite database.
Ollama is an optional Milestone 2 profile and is not started by default.

## Tests

```powershell
pytest -q
docker compose config
```
