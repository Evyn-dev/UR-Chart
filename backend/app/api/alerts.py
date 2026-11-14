from fastapi import APIRouter, Depends, Query
from app.auth import current_patient, get_db
from app.models import Alert
from app.schemas import Data, AlertCreate, AlertOut
from app.services.records import listing, save

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=Data[list[AlertOut]])
def index(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), patient=Depends(current_patient), db=Depends(get_db)):
    return {"data": listing(db, Alert, patient.id, limit, offset)}


@router.post("", response_model=Data[AlertOut], status_code=201)
def create(body: AlertCreate, patient=Depends(current_patient), db=Depends(get_db)):
    return {"data": save(db, Alert(patient_id=patient.id, **body.model_dump()))}
