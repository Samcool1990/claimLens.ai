# Ingestion contract

Validation is performed before extraction: filename extension, declared MIME, PDF signature,
file size, readability, encryption, page count, and structural opening.

SHA-256 is calculated before database lookup. A duplicate returns the existing document and
creates no policy, document, page, clause, or ingestion-run rows.

On new files, policy/version/document/pages/clauses are written in one SQLAlchemy transaction.
Extraction happens before that transaction. Page offsets are zero-based character offsets within
the extracted text of the referenced page.
