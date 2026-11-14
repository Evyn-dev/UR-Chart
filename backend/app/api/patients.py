from fastapi import APIRouter, Depends
from app.auth import current_patient, get_db
from app.schemas import Data, PatientOut, PatientPatch
from app.services.records import save
from sqlalchemy import select
from app.models import Medication
from app.services.medications import replace_schedule

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/me", response_model=Data[PatientOut])
def me(patient=Depends(current_patient)):
    return {"data": patient}


@router.patch("/me", response_model=Data[PatientOut])
def update(body: PatientPatch, patient=Depends(current_patient), db=Depends(get_db)):
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(patient, key, value)
    if "timezone" in body.model_fields_set:
        for medication in db.scalars(select(Medication).where(Medication.patient_id == patient.id, Medication.active.is_(True))):
            replace_schedule(db, medication, patient.timezone)
    return {"data": save(db, patient)}
