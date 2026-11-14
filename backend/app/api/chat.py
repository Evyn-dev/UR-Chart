from uuid import UUID
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy import select
from app.auth import current_patient, get_db
from app.models import Conversation, Message, RecoveryPlan, Medication, MedicationLog, Checkin, Alert, PatientAppointment
from app.schemas import Data, ChatCreate, ChatOut, ConversationOut, ConversationDetail
from app.services.records import owned, listing
from app.services import summaries
from app.services.ai import PatientContext, AIUnavailable, respond

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/conversations", response_model=Data[list[ConversationOut]])
def index(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), patient=Depends(current_patient), db=Depends(get_db)):
    return {"data": listing(db, Conversation, patient.id, limit, offset)}


@router.get("/conversations/{id}", response_model=Data[ConversationDetail])
def detail(id: UUID, patient=Depends(current_patient), db=Depends(get_db)):
    return {"data": owned(db, Conversation, id, patient.id)}


@router.post("/message", response_model=Data[ChatOut], status_code=201)
def message(body: ChatCreate, request: Request, patient=Depends(current_patient), db=Depends(get_db)):
    conversation = owned(db, Conversation, body.conversation_id, patient.id) if body.conversation_id else None
    recent = db.scalars(select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at.desc(), Message.id.desc()).limit(20)).all() if conversation else []
    history = [{"role": m.role, "content": m.content} for m in reversed(recent)]
    instructions = db.scalars(select(RecoveryPlan.approved_instructions).where(RecoveryPlan.patient_id == patient.id, RecoveryPlan.approved_by.is_not(None)).order_by(RecoveryPlan.created_at).limit(10)).all()
    # Only the currently authenticated patient's own records are exposed to AI.
    medications = db.scalars(select(Medication).where(
        Medication.patient_id == patient.id, Medication.active.is_(True)
    ).order_by(Medication.created_at.desc()).limit(10)).all()
    checkins = db.scalars(select(Checkin).where(
        Checkin.patient_id == patient.id
    ).order_by(Checkin.day.desc()).limit(7)).all()
    alerts = db.scalars(select(Alert).where(
        Alert.patient_id == patient.id
    ).order_by(Alert.created_at.desc()).limit(5)).all()
    # The local AI receives only this authenticated patient's recent dose logs.
    # Logged statuses are reported as entered, never inferred from missing events.
    current_day = datetime.now(ZoneInfo(patient.timezone)).date()
    lower_bound = datetime.combine(current_day - timedelta(days=6), datetime.min.time(), ZoneInfo(patient.timezone)).astimezone(timezone.utc)
    medication_names = {m.id: m.name for m in medications}
    dose_logs = db.scalars(select(MedicationLog).where(
        MedicationLog.medication_id.in_(list(medication_names)),
        MedicationLog.recorded_at >= lower_bound,
    ).order_by(MedicationLog.recorded_at.desc()).limit(45)).all() if medication_names else []
    upcoming = db.scalars(select(PatientAppointment).where(
        PatientAppointment.patient_id == patient.id,
        PatientAppointment.date_time >= datetime.now(timezone.utc)
    ).order_by(PatientAppointment.date_time).limit(5)).all()
    today_summary = summaries.medication_summary(db, patient, current_day, current_day)
    today_checkin = any(c.day == current_day for c in checkins)
    import json
    snapshot = json.dumps({
        "today_briefing": {
            "day": current_day.isoformat(),
            "checkin_recorded": today_checkin,
            "scheduled_dose_count": len(today_summary["today_doses"]),
            "dose_status_unrecorded_count": len(today_summary["unrecorded_doses"]),
            "important_note": "Unrecorded is not the same as a confirmed missed dose.",
        },
        "upcoming_appointments": [{
            "title": a.title, "date_time": a.date_time.isoformat(),
            "place": a.place,
        } for a in upcoming],
        "active_medications": [{
            "name": m.name, "dosage_as_entered": m.dosage,
            "schedule_as_entered": m.schedule
        } for m in medications],
        "recent_medication_dose_logs": [{
            "medication": medication_names.get(log.medication_id, "Medication"),
            "status_as_recorded": log.status,
            "recorded_at": log.recorded_at.isoformat(),
            "scheduled_for": log.scheduled_for.isoformat() if log.scheduled_for else None,
            "sample_note": log.note,
        } for log in dose_logs],
        "recent_checkins": [{
            "day": c.day.isoformat(), "pain_level": c.pain_level,
            "wellbeing": c.wellbeing, "symptoms_as_entered": c.symptoms,
            "activity_minutes": c.activity_minutes, "activity_type": c.activity_type,
            "patient_note": c.note
        } for c in checkins],
        "recent_alerts": [{
            "category": a.category, "severity": a.severity, "status": a.status
        } for a in alerts],
    }, default=str)
    try:
        answer = respond(request.app.state.ai, body.message, PatientContext(tuple(instructions), snapshot), history)
    except AIUnavailable:
        raise HTTPException(503, "AI service unavailable; no messages saved") from None
    if conversation is None:
        conversation = Conversation(patient_id=patient.id, title="Recovery conversation")
        db.add(conversation)
        db.flush()
    user_message = Message(conversation_id=conversation.id, role="user", content=body.message)
    assistant_message = Message(conversation_id=conversation.id, role="assistant", content=answer)
    db.add_all([user_message, assistant_message])
    db.commit()
    return {"data": {"conversation_id": conversation.id, "user_message": user_message, "assistant_message": assistant_message}}
