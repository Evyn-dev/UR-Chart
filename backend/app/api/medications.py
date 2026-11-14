from uuid import UUID
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from app.services import medications as service
from app.models import MedicationSchedule
from app.schemas.recovery import DoseHistory, ScheduleOut
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from app.auth import current_patient, get_db
from app.models import Medication, MedicationLog
from app.schemas import Data, MedicationCreate, MedicationPatch, MedicationOut, LogCreate, LogOut, MedicationAdherence, RefillStatus
from app.services.records import owned, listing, save

router = APIRouter(prefix="/medications", tags=["medications"])


@router.get("", response_model=Data[list[MedicationOut]])
def index(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), patient=Depends(current_patient), db=Depends(get_db)):
    return {"data": listing(db, Medication, patient.id, limit, offset)}


@router.post("", response_model=Data[MedicationOut], status_code=201)
def create(body: MedicationCreate, patient=Depends(current_patient), db=Depends(get_db)):
    data = body.model_dump(mode="json")
    record = Medication(patient_id=patient.id, **data)
    db.add(record)
    db.flush()
    service.replace_schedule(db, record, patient.timezone)
    return {"data": save(db, record)}


@router.patch("/{id}", response_model=Data[MedicationOut])
def update(id: UUID, body: MedicationPatch, patient=Depends(current_patient), db=Depends(get_db)):
    record = owned(db, Medication, id, patient.id)
    for key, value in body.model_dump(exclude_unset=True, mode="json").items():
        setattr(record, key, value)
    if {"reminder_times", "active"} & body.model_fields_set:
        service.replace_schedule(db, record, patient.timezone)
    return {"data": save(db, record)}


@router.post("/{id}/log", response_model=Data[LogOut], status_code=201)
def log(id: UUID, body: LogCreate, patient=Depends(current_patient), db=Depends(get_db)):
    medication = owned(db, Medication, id, patient.id)
    return {"data": service.log_dose(db, medication, body)}


@router.get("/{id}/logs", response_model=Data[list[LogOut]])
def logs(id: UUID, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), patient=Depends(current_patient), db=Depends(get_db)):
    medication = owned(db, Medication, id, patient.id)
    records = db.scalars(select(MedicationLog).where(MedicationLog.medication_id == medication.id).order_by(MedicationLog.recorded_at.desc(), MedicationLog.id).offset(offset).limit(limit)).all()
    return {"data": records}


@router.get("/{id}/adherence", response_model=Data[MedicationAdherence])
def adherence(id: UUID, start: date | None = None, end: date | None = None, patient=Depends(current_patient), db=Depends(get_db)):
    medication = owned(db, Medication, id, patient.id)
    end = end or datetime.now(ZoneInfo(patient.timezone)).date()
    start = start or end - timedelta(days=29)
    return {"data": service.adherence(db, medication, start, end)}


@router.get("/{id}/refill", response_model=Data[RefillStatus])
def refill(id: UUID, patient=Depends(current_patient), db=Depends(get_db)):
    medication = owned(db, Medication, id, patient.id)
    needed = (medication.supply_remaining <= medication.refill_threshold if medication.supply_remaining is not None and medication.refill_threshold is not None else None)
    return {"data": {"medication_id": medication.id, "supply_remaining": medication.supply_remaining, "refill_threshold": medication.refill_threshold, "refill_needed": needed}}


@router.get("/{id}/doses", response_model=Data[DoseHistory])
def doses(id: UUID, start: date, end: date, patient=Depends(current_patient), db=Depends(get_db)):
    medication = owned(db, Medication, id, patient.id)
    return {"data": service.dose_history(db, medication, start, end)}


@router.get("/{id}/schedules", response_model=Data[list[ScheduleOut]])
def schedules(id: UUID, patient=Depends(current_patient), db=Depends(get_db)):
    medication = owned(db, Medication, id, patient.id)
    return {"data": db.scalars(select(MedicationSchedule).where(MedicationSchedule.medication_id == medication.id).order_by(MedicationSchedule.effective_from)).all()}
