import hashlib
import io
import re
from dataclasses import dataclass
from pathlib import Path
import fitz
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..core.config import get_settings
from ..models.entities import Policy, PolicyVersion, Document, DocumentPage, Clause


class PdfValidationError(ValueError):
    pass


@dataclass
class ExtractedPage:
    index: int
    number: int
    text: str


@dataclass
class ExtractedClause:
    heading: str | None
    title: str | None
    text: str
    page_number: int
    start_offset: int
    end_offset: int


def fingerprint(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_pdf(data: bytes, filename: str, media_type: str = "") -> fitz.Document:
    settings = get_settings()
    if not filename.lower().endswith(".pdf"):
        raise PdfValidationError("The upload must have a .pdf filename.")
    if media_type not in ("", "application/pdf", "application/octet-stream"):
        raise PdfValidationError("Unsupported media type.")
    if len(data) > settings.max_upload_bytes:
        raise PdfValidationError("The PDF exceeds the configured upload limit.")
    if len(data) < 5 or not data.lstrip().startswith(b"%PDF-"):
        raise PdfValidationError("The file is not a readable PDF.")
    try:
        pdf = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise PdfValidationError("The PDF could not be read.") from exc
    if pdf.is_encrypted:
        pdf.close()
        raise PdfValidationError("Encrypted PDFs are not supported.")
    if pdf.page_count == 0:
        pdf.close()
        raise PdfValidationError("The PDF contains no pages.")
    if pdf.page_count > settings.max_pdf_pages:
        pdf.close()
        raise PdfValidationError("The PDF exceeds the configured page limit.")
    return pdf


def extract_pages(pdf: fitz.Document) -> list[ExtractedPage]:
    pages = []
    for index in range(pdf.page_count):
        text = pdf.load_page(index).get_text("text").replace("\r\n", "\n")
        pages.append(ExtractedPage(index, index + 1, text))
    return pages


def segment_page(page: ExtractedPage) -> list[ExtractedClause]:
    text = page.text
    heading_pattern = re.compile(
        r"(?m)^[ \t]*(?:\d+(?:\.\d+)*[.)]?[ \t]+[^\n]+|[A-Z][A-Z0-9][A-Z0-9 \-/]{2,}:?[ \t]*)$"
    )
    starts = [match.start() for match in heading_pattern.finditer(text)]
    boundaries = []
    if starts:
        boundaries = sorted(set([0] + starts))
    else:
        boundaries = [0] + [match.end() for match in re.finditer(r"\n\s*\n", text)]

    chunks: list[tuple[int, int]] = []
    for position, start in enumerate(boundaries):
        end = boundaries[position + 1] if position + 1 < len(boundaries) else len(text)
        if start < end:
            chunks.append((start, end))
    if not chunks:
        chunks = [(0, len(text))]

    result = []
    for start, end in chunks:
        raw = text[start:end].strip()
        if not raw:
            continue
        start = start + text[start:end].find(raw)
        if not text:
            continue
        end = start + len(raw)
        heading = raw.split("\n", 1)[0][:512]
        result.append(ExtractedClause(heading, heading, raw, page.number, start, end))
    return result


def _save_upload(filename: str, data: bytes, digest: str) -> str:
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename).name.replace("\\", "_")
    path = settings.upload_dir / f"{digest}-{safe_name}"
    if not path.exists():
        path.write_bytes(data)
    return str(path)


def ingest_pdf_bytes(db: Session, data: bytes, filename: str, media_type: str, metadata) -> tuple[Document, bool]:
    digest = fingerprint(data)
    existing = db.scalar(select(Document).where(Document.sha256 == digest))
    if existing:
        return existing, True

    pdf = validate_pdf(data, filename, media_type)
    try:
        pages = extract_pages(pdf)
    finally:
        pdf.close()
    clauses_by_page = [segment_page(p) for p in pages]
    try:
        policy = db.scalar(select(Policy).where(
            Policy.carrier == metadata.carrier,
            Policy.policy_number == metadata.policy_number,
            Policy.product_name == metadata.product_name))
        if policy is None:
            policy = Policy(carrier=metadata.carrier, policy_number=metadata.policy_number,
                            product_name=metadata.product_name, jurisdiction=metadata.jurisdiction,
                            policy_holder=metadata.policy_holder)
            db.add(policy)
            db.flush()

        version = db.scalar(select(PolicyVersion).where(
            PolicyVersion.policy_id == policy.id,
            PolicyVersion.effective_date == metadata.effective_date,
            PolicyVersion.expiry_date == metadata.expiry_date,
            PolicyVersion.version_label == metadata.version_label))
        if version is None:
            version = PolicyVersion(policy_id=policy.id, effective_date=metadata.effective_date,
                                    expiry_date=metadata.expiry_date, version_label=metadata.version_label,
                                    source_metadata=metadata.source_metadata)
            db.add(version)
            db.flush()

        document = Document(policy_version_id=version.id, filename=Path(filename).name,
                            media_type=media_type or "application/pdf", byte_size=len(data),
                            sha256=digest, validation_state="committed",
                            storage_location=_save_upload(filename, data, digest))
        db.add(document)
        db.flush()
        page_text_offset = 0
        for page in pages:
            db.add(DocumentPage(document_id=document.id, page_index=page.index,
                                page_number=page.number, text_length=len(page.text),
                                content_hash=hashlib.sha256(page.text.encode()).hexdigest()))
            page_text_offset += len(page.text) + 1
        ordinal = 0
        for page in pages:
            for clause in segment_page(page):
                db.add(Clause(document_id=document.id, policy_version_id=version.id,
                              heading=clause.heading, title=clause.title, text=clause.text,
                              page_number=clause.page_number, start_offset=clause.start_offset,
                              end_offset=clause.end_offset, ordinal=ordinal,
                              clause_type="unknown",
                              segmentation_method="deterministic-heading-number-blank-line"))
                ordinal += 1
        db.commit()
        db.refresh(document)
        return document, False
    except Exception:
        db.rollback()
        raise
