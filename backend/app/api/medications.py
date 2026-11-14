from uuid import UUID
from fastapi import APIRouter, Depends, Query
from app.auth import current_patient, get_db
from app.models import Medication, MedicationLog
from app.schemas import Data, MedicationCreate, MedicationPatch, MedicationOut, LogCreate, LogOut
from app.services.records import owned, listing, save

router = APIRouter(prefix="/medications", tags=["medications"])


@router.get("", response_model=Data[list[MedicationOut]])
def index(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), patient=Depends(current_patient), db=Depends(get_db)):
    return {"data": listing(db, Medication, patient.id, limit, offset)}


@router.post("", response_model=Data[MedicationOut], status_code=201)
def create(body: MedicationCreate, patient=Depends(current_patient), db=Depends(get_db)):
    return {"data": save(db, Medication(patient_id=patient.id, **body.model_dump()))}


@router.patch("/{id}", response_model=Data[MedicationOut])
def update(id: UUID, body: MedicationPatch, patient=Depends(current_patient), db=Depends(get_db)):
    record = owned(db, Medication, id, patient.id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    return {"data": save(db, record)}


@router.post("/{id}/log", response_model=Data[LogOut], status_code=201)
def log(id: UUID, body: LogCreate, patient=Depends(current_patient), db=Depends(get_db)):
    medication = owned(db, Medication, id, patient.id)
    return {"data": save(db, MedicationLog(medication_id=medication.id, **body.model_dump()))}
