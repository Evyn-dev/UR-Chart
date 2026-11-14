from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select
from app.auth import current_patient, get_db
from app.models import CaregiverRelationship, CaregiverAudit
from app.schemas import Data
from app.schemas.support import CaregiverInvite, CaregiverChange, InvitationResponse, Versioned, RelationshipOut, CaregiverAuditOut, CaregiverDashboard
from app.services import caregivers

router = APIRouter(tags=["caregiver sharing"])


@router.post("/caregivers/invitations", response_model=Data[RelationshipOut], status_code=201)
def invite(body: CaregiverInvite, request: Request, patient=Depends(current_patient), db=Depends(get_db)):
    return {"data": caregivers.invite(db, patient, body, request.app.state.settings)}


@router.get("/caregivers", response_model=Data[list[RelationshipOut]])
def outgoing(status: Literal["pending", "active", "declined", "revoked"] | None = None, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), patient=Depends(current_patient), db=Depends(get_db)):
    query = select(CaregiverRelationship).where(CaregiverRelationship.patient_id == patient.id)
    if status:
        query = query.where(CaregiverRelationship.status == status)
    return {"data": db.scalars(query.order_by(CaregiverRelationship.created_at.desc(), CaregiverRelationship.id).offset(offset).limit(limit)).all()}


@router.patch("/caregivers/{id}/permissions", response_model=Data[RelationshipOut])
def permissions(id: UUID, body: CaregiverChange, patient=Depends(current_patient), db=Depends(get_db)):
    return {"data": caregivers.change_permissions(db, patient, id, body)}


@router.post("/caregivers/{id}/revoke", response_model=Data[RelationshipOut])
def revoke(id: UUID, body: Versioned, patient=Depends(current_patient), db=Depends(get_db)):
    return {"data": caregivers.revoke(db, patient, id, body)}


@router.get("/caregivers/{id}/audit", response_model=Data[list[CaregiverAuditOut]])
def audit(id: UUID, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), patient=Depends(current_patient), db=Depends(get_db)):
    relationship = caregivers.owner_record(db, patient, id)
    return {"data": db.scalars(select(CaregiverAudit).where(CaregiverAudit.relationship_id == relationship.id,
        CaregiverAudit.patient_id == patient.id).order_by(CaregiverAudit.created_at.desc(), CaregiverAudit.id).offset(offset).limit(limit)).all()}


@router.get("/caregiver/invitations", response_model=Data[list[RelationshipOut]])
def incoming(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), patient=Depends(current_patient), db=Depends(get_db)):
    return {"data": db.scalars(select(CaregiverRelationship).where(CaregiverRelationship.caregiver_user_id == patient.user_id,
        CaregiverRelationship.status == "pending").order_by(CaregiverRelationship.created_at.desc(), CaregiverRelationship.id).offset(offset).limit(limit)).all()}


@router.post("/caregiver/invitations/{id}/respond", response_model=Data[RelationshipOut])
def respond(id: UUID, body: InvitationResponse, patient=Depends(current_patient), db=Depends(get_db)):
    return {"data": caregivers.respond(db, patient, id, body)}


@router.get("/caregiver/relationships", response_model=Data[list[RelationshipOut]])
def active(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), patient=Depends(current_patient), db=Depends(get_db)):
    return {"data": db.scalars(select(CaregiverRelationship).where(CaregiverRelationship.caregiver_user_id == patient.user_id,
        CaregiverRelationship.status == "active").order_by(CaregiverRelationship.created_at.desc(), CaregiverRelationship.id).offset(offset).limit(limit)).all()}


@router.get("/caregiver/relationships/{id}/dashboard", response_model=Data[CaregiverDashboard], response_model_exclude_none=True)
def dashboard(id: UUID, response: Response, limit: int = Query(20, ge=1, le=50), offset: int = Query(0, ge=0), patient=Depends(current_patient), db=Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return {"data": caregivers.dashboard(db, patient, id, limit, offset)}
