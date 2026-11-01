import hashlib
import pytest
from app.services.pdf_ingestion import fingerprint, validate_pdf, PdfValidationError


def test_fingerprint():
    assert fingerprint(b"claimlens") == hashlib.sha256(b"claimlens").hexdigest()


def test_rejects_non_pdf():
    with pytest.raises(PdfValidationError):
        validate_pdf(b"not pdf", "policy.txt")
