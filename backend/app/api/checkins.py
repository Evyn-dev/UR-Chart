from fastapi import APIRouter, Depends, Query
from app.auth import current_patient, get_db
from app.models import Checkin
from app.schemas import Data, CheckinCreate, CheckinOut
from app.services.records import listing, save

router = APIRouter(prefix="/checkins", tags=["checkins"])


@router.get("", response_model=Data[list[CheckinOut]])
def index(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), patient=Depends(current_patient), db=Depends(get_db)):
    return {"data": listing(db, Checkin, patient.id, limit, offset)}


@router.post("", response_model=Data[CheckinOut], status_code=201)
def create(body: CheckinCreate, patient=Depends(current_patient), db=Depends(get_db)):
    return {"data": save(db, Checkin(patient_id=patient.id, **body.model_dump()))}
