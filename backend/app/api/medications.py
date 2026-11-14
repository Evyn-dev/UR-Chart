from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
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
    return {"data": save(db, Medication(patient_id=patient.id, **data))}


@router.patch("/{id}", response_model=Data[MedicationOut])
def update(id: UUID, body: MedicationPatch, patient=Depends(current_patient), db=Depends(get_db)):
    record = owned(db, Medication, id, patient.id)
    for key, value in body.model_dump(exclude_unset=True, mode="json").items():
        setattr(record, key, value)
    return {"data": save(db, record)}


@router.post("/{id}/log", response_model=Data[LogOut], status_code=201)
def log(id: UUID, body: LogCreate, patient=Depends(current_patient), db=Depends(get_db)):
    medication = owned(db, Medication, id, patient.id)
    return {"data": save(db, MedicationLog(medication_id=medication.id, **body.model_dump()))}


@router.get("/{id}/logs", response_model=Data[list[LogOut]])
def logs(id: UUID, patient=Depends(current_patient), db=Depends(get_db)):
    medication = owned(db, Medication, id, patient.id)
    records = db.scalars(select(MedicationLog).where(MedicationLog.medication_id == medication.id).order_by(MedicationLog.recorded_at.desc())).all()
    return {"data": records}


@router.get("/{id}/adherence", response_model=Data[MedicationAdherence])
def adherence(id: UUID, patient=Depends(current_patient), db=Depends(get_db)):
    medication = owned(db, Medication, id, patient.id)
    counts = dict(db.execute(select(MedicationLog.status, func.count()).where(MedicationLog.medication_id == medication.id).group_by(MedicationLog.status)).all())
    taken, skipped = counts.get("taken", 0), counts.get("skipped", 0)
    total = taken + skipped
    return {"data": {"taken": taken, "skipped": skipped, "total_logged": total, "adherence_percent": round(100 * taken / total, 1) if total else None}}


@router.get("/{id}/refill", response_model=Data[RefillStatus])
def refill(id: UUID, patient=Depends(current_patient), db=Depends(get_db)):
    medication = owned(db, Medication, id, patient.id)
    needed = (medication.supply_remaining <= medication.refill_threshold if medication.supply_remaining is not None and medication.refill_threshold is not None else None)
    return {"data": {"medication_id": medication.id, "supply_remaining": medication.supply_remaining, "refill_threshold": medication.refill_threshold, "refill_needed": needed}}
