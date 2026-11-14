from fastapi import APIRouter, Depends, Query, Request
from datetime import date
from uuid import UUID
from app.auth import current_patient, get_db
from app.models import Checkin
from app.schemas import Data, CheckinCreate, CheckinOut
from app.services.records import save
from app.services.records import owned
from app.services import checkins as service, risk
from app.schemas.recovery import TrendSummary, RiskResult

router = APIRouter(prefix="/checkins", tags=["checkins"])


@router.get("", response_model=Data[list[CheckinOut]])
def index(start: date | None = None, end: date | None = None, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), patient=Depends(current_patient), db=Depends(get_db)):
    return {"data": service.history(db, patient.id, start, end, limit, offset)}


@router.post("", response_model=Data[CheckinOut], status_code=201)
def create(body: CheckinCreate, request: Request, patient=Depends(current_patient), db=Depends(get_db)):
    record = Checkin(patient_id=patient.id, **body.model_dump())
    db.add(record)
    db.flush()
    risk.evaluate(db, record, request.app.state.settings)
    return {"data": save(db, record)}


@router.get("/trends", response_model=Data[TrendSummary])
def trends(start: date, end: date, patient=Depends(current_patient), db=Depends(get_db)):
    return {"data": service.trends(db, patient.id, start, end)}


@router.get("/{id}", response_model=Data[CheckinOut])
def detail(id: UUID, patient=Depends(current_patient), db=Depends(get_db)):
    return {"data": owned(db, Checkin, id, patient.id)}


@router.get("/{id}/risk", response_model=Data[RiskResult])
def assessment(id: UUID, request: Request, patient=Depends(current_patient), db=Depends(get_db)):
    record = owned(db, Checkin, id, patient.id)
    # Re-evaluate when rules or screening-engine versions change, including
    # records created before a newer screening implementation was deployed.
    risk.evaluate(db, record, request.app.state.settings)
    db.commit()
    return {"data": risk.result(db, record)}


@router.post("/{id}/evaluate", response_model=Data[RiskResult])
def evaluate(id: UUID, request: Request, patient=Depends(current_patient), db=Depends(get_db)):
    record = owned(db, Checkin, id, patient.id)
    risk.evaluate(db, record, request.app.state.settings)
    db.commit()
    return {"data": risk.result(db, record)}
