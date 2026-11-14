from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy import select
from app.auth import current_patient, get_db
from app.models import Medication, MedicationLog, Checkin, Alert
from app.schemas import Data, LogOut, CheckinOut, AlertOut
from app.schemas.support import LogCorrection, CheckinCorrection, AlertAction, AuditOut
from app.services.records import owned
from app.services import corrections

router = APIRouter(tags=["corrections"])


@router.patch("/medications/{id}/logs/{log_id}", response_model=Data[LogOut])
def correct_log(id: UUID, log_id: UUID, body: LogCorrection, patient=Depends(current_patient), db=Depends(get_db)):
    return {"data": corrections.log_correction(db, patient, owned(db, Medication, id, patient.id), log_id, body)}


@router.get("/medications/{id}/logs/{log_id}/audit", response_model=Data[list[AuditOut]])
def log_audit(id: UUID, log_id: UUID, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), patient=Depends(current_patient), db=Depends(get_db)):
    medication = owned(db, Medication, id, patient.id)
    if not db.scalar(select(MedicationLog).where(MedicationLog.id == str(log_id), MedicationLog.medication_id == medication.id)):
        raise HTTPException(404, "Log not found")
    return {"data": corrections.history(db, patient.id, "medication_log", log_id, limit, offset)}


@router.patch("/checkins/{id}", response_model=Data[CheckinOut])
def correct_checkin(id: UUID, body: CheckinCorrection, request: Request, patient=Depends(current_patient), db=Depends(get_db)):
    return {"data": corrections.checkin_correction(db, patient, owned(db, Checkin, id, patient.id), body, request.app.state.settings)}


@router.get("/checkins/{id}/audit", response_model=Data[list[AuditOut]])
def checkin_audit(id: UUID, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), patient=Depends(current_patient), db=Depends(get_db)):
    owned(db, Checkin, id, patient.id)
    return {"data": corrections.history(db, patient.id, "checkin", id, limit, offset)}


@router.post("/alerts/{id}/actions", response_model=Data[AlertOut])
def change_alert(id: UUID, body: AlertAction, patient=Depends(current_patient), db=Depends(get_db)):
    return {"data": corrections.alert_action(db, patient, owned(db, Alert, id, patient.id), body)}


@router.get("/alerts/{id}/audit", response_model=Data[list[AuditOut]])
def alert_audit(id: UUID, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), patient=Depends(current_patient), db=Depends(get_db)):
    owned(db, Alert, id, patient.id)
    return {"data": corrections.history(db, patient.id, "alert", id, limit, offset)}
