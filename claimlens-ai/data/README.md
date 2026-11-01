# Runtime data

- `claimlens.db` is the system of record for ClaimLens policies, versions, documents, pages,
  clauses, and ingestion runs.
- `uploads/` contains uploaded policy PDFs named with their SHA-256 fingerprint.
- Docker Compose bind-mounts this directory at `/data` in the API container.
- Runtime files are not example fixtures. The sample policy PDF is in `evaluation/`.
