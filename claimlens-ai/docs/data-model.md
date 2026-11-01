# Data model

Policies are grouped by carrier, policy number, and product. Versions are bounded by effective
and expiry dates. Documents are SHA-256 deduplicated. Pages retain extraction content hashes,
while clauses retain a page number and character offsets.

SQLite foreign keys are enabled and startup creates the SQLAlchemy schema. Runtime uploads are
stored under the configured upload directory; a generated path is never derived from untrusted
user input.
