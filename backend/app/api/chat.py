from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy import select
from app.auth import current_patient, get_db
from app.models import Conversation, Message, RecoveryPlan, Medication, Checkin, Alert
from app.schemas import Data, ChatCreate, ChatOut, ConversationOut, ConversationDetail
from app.services.records import owned, listing
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
    # Read only authenticated patient's own existing team records.
    medications = db.scalars(select(Medication).where(
        Medication.patient_id == patient.id, Medication.active.is_(True)
    ).order_by(Medication.created_at.desc()).limit(10)).all()
    checkins = db.scalars(select(Checkin).where(
        Checkin.patient_id == patient.id
    ).order_by(Checkin.day.desc()).limit(5)).all()
    alerts = db.scalars(select(Alert).where(
        Alert.patient_id == patient.id
    ).order_by(Alert.created_at.desc()).limit(5)).all()
    snapshot = {
        "medications": [{"name": m.name, "schedule": m.schedule} for m in medications],
        "checkins": [{"day": c.day.isoformat(), "wellbeing": c.wellbeing,
                      "pain_level": c.pain_level} for c in checkins],
        "recent_alerts": [{"severity": a.severity, "category": a.category,
                           "status": a.status} for a in alerts],
    }
    import json
    try:
        answer = respond(request.app.state.ai, body.message,
                         PatientContext(tuple(instructions), json.dumps(snapshot)), history)
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
