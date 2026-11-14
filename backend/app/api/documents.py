"""Consent-checked small-file attachments for the fictional UR Chart demo.

Files are private by default. Caregiver access requires an *active* accepted
relationship, plus per-file sharing by the patient. Caregiver contributions are
visible to the patient and their own uploader, never every caregiver.
No client-supplied patient ID is trusted for ownership.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from app.auth import current_patient, get_db
from app.models import CaregiverRelationship, SharedDocument

router = APIRouter(prefix="/documents", tags=["shared documents"])
MAX_BYTES = 3 * 1024 * 1024
ALLOWED = {"application/pdf": ".pdf", "image/png": ".png",
           "image/jpeg": ".jpg", "text/plain": ".txt"}


class SharingChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    shared_with_caregivers: bool


def is_valid_content(data: bytes, mime: str) -> bool:
    if mime == "application/pdf":
        return data.startswith(b"%PDF-")
    if mime == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if mime == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if mime == "text/plain":
        try:
            content = data.decode("utf-8")
            return "\x00" not in content
        except UnicodeDecodeError:
            return False
    return False


def relationships(db, user_id):
    return db.scalars(select(CaregiverRelationship).where(
        CaregiverRelationship.caregiver_user_id == user_id,
        CaregiverRelationship.status == "active",
    )).all()


def active_for(db, user_id, patient_id):
    return db.scalar(select(CaregiverRelationship).where(
        CaregiverRelationship.caregiver_user_id == user_id,
        CaregiverRelationship.patient_id == patient_id,
        CaregiverRelationship.status == "active",
    ))


def visible(db, actor, document):
    if document.patient_id == actor.id:
        return True
    rel = active_for(db, actor.user_id, document.patient_id)
    if not rel:
        return False
    return bool(document.shared_with_caregivers or (
        document.uploader_user_id == actor.user_id
        and document.uploader_relationship_id == rel.id
    ))


def metadata(doc, actor):
    return {
        "id": doc.id, "name": doc.name, "content_type": doc.content_type,
        "byte_size": doc.byte_size, "created_at": doc.created_at.isoformat(),
        "patient_id": doc.patient_id, "shared_with_caregivers": doc.shared_with_caregivers,
        "uploader_role": doc.uploader_role,
        "can_manage": doc.patient_id == actor.id,
    }


@router.get("")
def list_documents(actor=Depends(current_patient), db=Depends(get_db)):
    rels = relationships(db, actor.user_id)
    accessible_patient_ids = [rel.patient_id for rel in rels]
    rows = db.scalars(select(SharedDocument).where(
        SharedDocument.patient_id.in_([actor.id, *accessible_patient_ids])
    ).order_by(SharedDocument.created_at.desc()).limit(100)).all()
    return {"data": [metadata(doc, actor) for doc in rows if visible(db, actor, doc)]}


@router.post("/upload")
async def upload_document(request: Request, actor=Depends(current_patient), db=Depends(get_db)):
    # Body is a raw file; reject oversized uploads while streaming, not after buffering.
    mime = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if mime not in ALLOWED:
        raise HTTPException(415, "Allowed types: PDF, PNG, JPEG, or UTF-8 TXT")
    if (length := request.headers.get("content-length")):
        try:
            if int(length) > MAX_BYTES:
                raise HTTPException(413, "Maximum document size is 3 MB")
        except ValueError:
            raise HTTPException(400, "Invalid content length")
    filename = request.headers.get("x-document-name", "").strip()
    filename = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if not filename or len(filename) > 180 or any(ord(ch) < 32 for ch in filename):
        raise HTTPException(422, "Choose a valid file name under 181 characters")
    allowed_extension = ALLOWED[mime]
    if not filename.lower().endswith(allowed_extension) and not (
        mime == "image/jpeg" and filename.lower().endswith(".jpeg")
    ):
        raise HTTPException(415, "File extension does not match the document type")
    target_id = request.headers.get("x-target-patient-id", "").strip()
    relationship = None
    if target_id and target_id != actor.id:
        relationship = active_for(db, actor.user_id, target_id)
        if relationship is None:
            raise HTTPException(403, "Only an accepted caregiver may upload to this patient")
    patient_id = target_id or actor.id
    parts = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_BYTES:
            raise HTTPException(413, "Maximum document size is 3 MB")
        parts.append(chunk)
    data = b"".join(parts)
    if not data or not is_valid_content(data, mime):
        raise HTTPException(422, "Empty or invalid file content")
    doc = SharedDocument(
        patient_id=patient_id, uploader_user_id=actor.user_id,
        uploader_role="caregiver" if relationship else "patient",
        uploader_relationship_id=relationship.id if relationship else None,
        name=filename, content_type=mime, byte_size=total,
        payload=data, shared_with_caregivers=False,
    )
    db.add(doc)
    db.commit()
    return {"data": metadata(doc, actor)}


@router.get("/{document_id}")
def download_document(document_id: UUID, actor=Depends(current_patient), db=Depends(get_db)):
    doc = db.get(SharedDocument, str(document_id))
    if doc is None or not visible(db, actor, doc):
        raise HTTPException(404, "Document not found")
    safe_name = "".join(ch for ch in doc.name if 32 <= ord(ch) < 127 and ch not in '"\\') or "document"
    return Response(content=doc.payload, media_type=doc.content_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"',
                 "X-Content-Type-Options": "nosniff",
                 "Cache-Control": "no-store, private",
                 "Content-Security-Policy": "default-src 'none'; sandbox"})


@router.patch("/{document_id}/sharing")
def update_sharing(document_id: UUID, body: SharingChange,
                   actor=Depends(current_patient), db=Depends(get_db)):
    doc = db.get(SharedDocument, str(document_id))
    if doc is None or doc.patient_id != actor.id:
        raise HTTPException(404, "Document not found")
    doc.shared_with_caregivers = body.shared_with_caregivers
    db.commit()
    return {"data": metadata(doc, actor)}


@router.delete("/{document_id}")
def delete_document(document_id: UUID, actor=Depends(current_patient), db=Depends(get_db)):
    doc = db.get(SharedDocument, str(document_id))
    if doc is None or doc.patient_id != actor.id:
        raise HTTPException(404, "Document not found")
    db.delete(doc)
    db.commit()
    return {"data": {"deleted": True}}
