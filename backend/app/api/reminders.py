"""Authenticated Reminders-style tasks, separate from clinical safety alerts."""
from datetime import timezone
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from app.auth import current_patient, get_db
from app.models.reminders import PersonalReminder
from app.schemas import Data
from app.schemas.reminders import ReminderCreate, ReminderAction, ReminderOut
from app.services import reminders as service

router = APIRouter(prefix="/reminders", tags=["personal-reminders"])


@router.get("", response_model=Data[list[ReminderOut]])
def list_reminders(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                   patient=Depends(current_patient), db=Depends(get_db)):
    items = db.scalars(select(PersonalReminder).where(
        PersonalReminder.patient_id == patient.id,
    ).order_by(PersonalReminder.due_at, PersonalReminder.id).limit(limit).offset(offset)).all()
    return {"data": items}


@router.post("", response_model=Data[ReminderOut], status_code=201)
def create(body: ReminderCreate, patient=Depends(current_patient), db=Depends(get_db)):
    item = PersonalReminder(patient_id=patient.id, **{
        **body.model_dump(), "due_at": body.due_at.astimezone(timezone.utc)
    })
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"data": item}


@router.post("/{id}/action", response_model=Data[ReminderOut | None])
def action(id: UUID, body: ReminderAction, patient=Depends(current_patient), db=Depends(get_db)):
    item = service.owned(db, patient.id, id)
    return {"data": service.apply_action(db, item, body.action)}
