import asyncio
from datetime import date
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from ..db.session import get_db
from ..core.config import get_settings
from ..models.entities import Policy, PolicyVersion, Document, DocumentPage, Clause
from ..schemas.ingestion import PolicyCreate, PolicyMetadata, PolicyVersionCreate
from ..services.pdf_ingestion import PdfValidationError, ingest_pdf_bytes
from ..services.serialization import policy_dict, version_dict, document_dict

router = APIRouter(prefix="/api/v1")


@router.post("/policies", status_code=status.HTTP_201_CREATED)
def register_policy(payload: PolicyCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(Policy).where(
        Policy.carrier == payload.carrier,
        Policy.policy_number == payload.policy_number,
        Policy.product_name == payload.product_name))
    if existing:
        return policy_dict(existing)
    policy = Policy(**payload.model_dump())
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy_dict(policy)


@router.post("/policies/{policy_id}/versions", status_code=status.HTTP_201_CREATED)
def register_policy_version(policy_id: int, payload: PolicyVersionCreate, db: Session = Depends(get_db)):
    policy = db.get(Policy, policy_id)
    if policy is None:
        raise HTTPException(404, "Policy not found.")
    existing = db.scalar(select(PolicyVersion).where(
        PolicyVersion.policy_id == policy_id,
        PolicyVersion.effective_date == payload.effective_date,
        PolicyVersion.expiry_date == payload.expiry_date,
        PolicyVersion.version_label == payload.version_label))
    if existing:
        return version_dict(existing)
    version = PolicyVersion(policy_id=policy_id, **payload.model_dump())
    db.add(version)
    db.commit()
    db.refresh(version)
    return version_dict(version)


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "healthy", "database": "connected", "milestone": 1}


def metadata_from_form(
    carrier: str = Form(...), policy_number: str = Form(...), product_name: str = Form(...),
    jurisdiction: str | None = Form(None), policy_holder: str | None = Form(None),
    effective_date: date = Form(...), expiry_date: date = Form(...),
    version_label: str = Form("1.0"), source_metadata: str | None = Form(None),
) -> PolicyMetadata:
    return PolicyMetadata(carrier=carrier, policy_number=policy_number, product_name=product_name,
                          jurisdiction=jurisdiction, policy_holder=policy_holder,
                          effective_date=effective_date, expiry_date=expiry_date,
                          version_label=version_label, source_metadata=source_metadata)


@router.post("/documents/ingest")
async def ingest(
    file: UploadFile = File(...),
    carrier: str = Form(...), policy_number: str = Form(...), product_name: str = Form(...),
    jurisdiction: str | None = Form(None), policy_holder: str | None = Form(None),
    effective_date: date = Form(...), expiry_date: date = Form(...),
    version_label: str = Form("1.0"), source_metadata: str | None = Form(None),
    db: Session = Depends(get_db),
):
    try:
        metadata = metadata_from_form(carrier, policy_number, product_name, jurisdiction, policy_holder,
                                      effective_date, expiry_date, version_label, source_metadata)
        data = await asyncio.to_thread(file.file.read)
        if len(data) > get_settings().max_upload_bytes:
            raise PdfValidationError("The PDF exceeds the configured upload limit.")
        document, duplicate = ingest_pdf_bytes(db, data, file.filename or "document.pdf",
                                               file.content_type or "", metadata)
        version = db.get(PolicyVersion, document.policy_version_id)
        policy = db.get(Policy, version.policy_id)
        pages = db.scalar(select(func.count(DocumentPage.id)).where(DocumentPage.document_id == document.id))
        clauses = db.scalar(select(func.count(Clause.id)).where(Clause.document_id == document.id))
        return {"document": document_dict(document), "policy": policy_dict(policy), "version": version_dict(version),
                "duplicate": duplicate, "page_count": pages, "clause_count": clauses}
    except PdfValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_url=False)) from exc


@router.get("/documents/{document_id}")
def document_detail(document_id: int, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(404, "Document not found.")
    return document_dict(document)


@router.get("/documents/{document_id}/pages")
def pages(document_id: int, db: Session = Depends(get_db)):
    if not db.get(Document, document_id):
        raise HTTPException(404, "Document not found.")
    rows = db.scalars(select(DocumentPage).where(DocumentPage.document_id == document_id).order_by(DocumentPage.page_number))
    return [{"id": x.id, "page_index": x.page_index, "page_number": x.page_number,
             "text_length": x.text_length, "content_hash": x.content_hash} for x in rows]


@router.get("/documents/{document_id}/clauses")
def clauses(document_id: int, db: Session = Depends(get_db)):
    if not db.get(Document, document_id):
        raise HTTPException(404, "Document not found.")
    rows = db.scalars(select(Clause).where(Clause.document_id == document_id).order_by(Clause.ordinal))
    return [{"id": x.id, "heading": x.heading, "title": x.title, "text": x.text,
             "page_number": x.page_number, "start_offset": x.start_offset, "end_offset": x.end_offset,
             "ordinal": x.ordinal, "clause_type": x.clause_type,
             "segmentation_method": x.segmentation_method} for x in rows]


@router.get("/policies/{policy_id}/versions")
def versions(policy_id: int, db: Session = Depends(get_db)):
    if not db.get(Policy, policy_id):
        raise HTTPException(404, "Policy not found.")
    rows = db.scalars(select(PolicyVersion).where(PolicyVersion.policy_id == policy_id).order_by(PolicyVersion.effective_date))
    return [version_dict(x) for x in rows]


@router.post("/policies/{policy_id}/versions/{version_id}/documents", status_code=status.HTTP_202_ACCEPTED)
async def ingest_existing(policy_id: int, version_id: int, file: UploadFile = File(...),
                          db: Session = Depends(get_db)):
    policy = db.get(Policy, policy_id)
    version = db.get(PolicyVersion, version_id)
    if policy is None or version is None or version.policy_id != policy_id:
        raise HTTPException(404, "Policy version not found.")
    metadata = PolicyMetadata(
        carrier=policy.carrier, policy_number=policy.policy_number, product_name=policy.product_name,
        jurisdiction=policy.jurisdiction, policy_holder=policy.policy_holder,
        effective_date=version.effective_date, expiry_date=version.expiry_date,
        version_label=version.version_label, source_metadata=version.source_metadata)
    try:
        data = await asyncio.to_thread(file.file.read)
        if len(data) > get_settings().max_upload_bytes:
            raise PdfValidationError("The PDF exceeds the configured upload limit.")
        document, duplicate = ingest_pdf_bytes(db, data, file.filename or "document.pdf",
                                               file.content_type or "", metadata)
        return {"document": document_dict(document), "duplicate": duplicate}
    except PdfValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
