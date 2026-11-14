"""Consent-gated engagement APIs for fictional hackathon use.

Emergency activation never calls 911. Use the immediate tel:911 user action.
Caregiver SMS/phone require explicit double opt-in and separately configured delivery.
"""
from datetime import datetime, timedelta, timezone, date
from typing import Literal
import re
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select
from app.auth import current_patient, get_db
from app.models import (
    Patient, Medication, MedicationLog, Checkin, RecoveryPlan, CaregiverRelationship,
    EmergencyContact, EmergencyEvent, CaregiverNote, PatientAppointment, EmergencyMedicalCard,
)
from app.services import summaries

router = APIRouter(prefix="/engagement", tags=["recovery support"])
UTC = timezone.utc


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ContactSetting(Strict):
    relationship_id: str = Field(min_length=36, max_length=36)
    priority: int = Field(default=1, ge=1, le=2)
    enabled: bool = False
    contact_name: str = Field(default="Caregiver", min_length=1, max_length=100)


class ContactOptIn(Strict):
    relationship_id: str = Field(min_length=36, max_length=36)
    phone: str = Field(min_length=8, max_length=24)
    consent: bool


class EmergencyRequest(Strict):
    share_location: bool = False
    location: str | None = Field(default=None, max_length=140)


class CaregiverNoteInput(Strict):
    relationship_id: str = Field(min_length=36, max_length=36)
    body: str = Field(min_length=1, max_length=700)


class AppointmentInput(Strict):
    date_time: datetime
    title: str = Field(min_length=1, max_length=150)
    place: str | None = Field(default=None, max_length=180)
    notes: str | None = Field(default=None, max_length=500)



class MedicalCardInput(Strict):
    allergies: list[str] = Field(default_factory=list, max_length=15)
    conditions: list[str] = Field(default_factory=list, max_length=15)
    note: str | None = Field(default=None, max_length=700)


def clean_card(body):
    if any(not item.strip() or len(item) > 80 for item in body.allergies + body.conditions):
        raise HTTPException(422, "Medical card entries must contain 1–80 characters")
    return {"allergies": [item.strip() for item in body.allergies],
            "conditions": [item.strip() for item in body.conditions], "note": body.note}


@router.get("/medical-card")
def medical_card(patient=Depends(current_patient), db=Depends(get_db)):
    row = db.scalar(select(EmergencyMedicalCard).where(
        EmergencyMedicalCard.patient_id == patient.id))
    return {"data": {"allergies": row.allergies if row else [],
                     "conditions": row.conditions if row else [], "note": row.note if row else None,
                     "warning": "Patient-entered or fictional data; not verified by a clinician."}}


@router.post("/medical-card")
def update_medical_card(body: MedicalCardInput, patient=Depends(current_patient), db=Depends(get_db)):
    row = db.scalar(select(EmergencyMedicalCard).where(
        EmergencyMedicalCard.patient_id == patient.id))
    if row is None:
        row = EmergencyMedicalCard(patient_id=patient.id)
        db.add(row)
    data = clean_card(body)
    row.allergies = data["allergies"]
    row.conditions = data["conditions"]
    row.note = data["note"]
    db.commit()
    return {"data": {**data, "warning": "Patient-entered data; not verified by a clinician."}}

def public_contact(row):
    return {"relationship_id": row.relationship_id, "priority": row.priority,
            "enabled": row.enabled, "contact_name": row.contact_name,
            "caregiver_opted_in": row.caregiver_opted_in,
            "phone_last_four": row.phone[-4:] if row.phone else None}


def public_event(row):
    return {"id": row.id, "created_at": row.created_at.isoformat(),
            "status": row.status, "share_location": row.share_location,
            "location": row.location if row.share_location else None,
            "notifications": row.notifications or [],
            "acknowledged_at": row.acknowledged_at.isoformat() if row.acknowledged_at else None,
            "acknowledged_by": row.acknowledged_by}


def relationship(db, row_id, patient_id=None, caregiver_user_id=None):
    q = select(CaregiverRelationship).where(
        CaregiverRelationship.id == row_id, CaregiverRelationship.status == "active")
    if patient_id is not None:
        q = q.where(CaregiverRelationship.patient_id == patient_id)
    if caregiver_user_id is not None:
        q = q.where(CaregiverRelationship.caregiver_user_id == caregiver_user_id)
    result = db.scalar(q)
    if result is None:
        raise HTTPException(403, "An accepted caregiver relationship is required")
    return result


def allowed_contact(db, row):
    rel = relationship(db, row.relationship_id, patient_id=row.patient_id)
    if "alerts" not in rel.permissions or "emergency" not in rel.alert_severities:
        return False
    return row.enabled and row.caregiver_opted_in and bool(row.phone)


def dispatch(settings, phone, text):
    # Never deliver real calls/SMS from shared demo identities or test environments.
    allowed = (
        settings.app_env == "production"
        and settings.live_caregiver_notifications
        and not settings.demo_auth_enabled and not settings.hosted_demo_code_hash
        and settings.supabase_url and settings.twilio_account_sid
        and settings.twilio_auth_token and settings.twilio_from_number
    )
    if not allowed:
        return {"sms": "demo_only_not_sent", "call": "demo_only_not_sent"}
    endpoint = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/"
    auth = (settings.twilio_account_sid, settings.twilio_auth_token)
    result = {}
    try:
        with httpx.Client(timeout=8) as client:
            sms = client.post(endpoint + "Messages.json", data={
                "To": phone, "From": settings.twilio_from_number, "Body": text,
            }, auth=auth)
            result["sms"] = "provider_accepted" if sms.status_code in (200, 201) else "provider_rejected"
            # TwiML is spoken by Twilio on the caregiver phone, not a 911 autodial.
            call = client.post(endpoint + "Calls.json", data={
                "To": phone, "From": settings.twilio_from_number,
                "Twiml": "<Response><Say>" + escape(text[:250]) + "</Say></Response>",
            }, auth=auth)
            result["call"] = "provider_accepted" if call.status_code in (200, 201) else "provider_rejected"
    except httpx.HTTPError:
        result.setdefault("sms", "delivery_error")
        result.setdefault("call", "delivery_error")
    return result


def notify(db, patient, event, priority, settings):
    contacts = db.scalars(select(EmergencyContact).where(
        EmergencyContact.patient_id == patient.id, EmergencyContact.priority == priority,
    )).all()
    attempts = list(event.notifications or [])
    for contact in contacts:
        if not allowed_contact(db, contact):
            continue
        message = (
            f"UR Chart alert: {patient.display_name} activated Emergency Connect at "
            f"{datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}. "
            "If this is a real emergency, contact emergency services yourself. "
            "This alert does not mean help has arrived."
        )
        if event.share_location and event.location:
            message += " Shared location: " + event.location
        result = dispatch(settings, contact.phone, message)
        attempts.append({"relationship_id": contact.relationship_id,
                         "priority": priority, "sms": result["sms"],
                         "call": result["call"], "attempted_at": datetime.now(UTC).isoformat()})
    if not any(i["priority"] == priority for i in attempts):
        attempts.append({"priority": priority, "sms": "not_configured",
                         "call": "not_configured", "attempted_at": datetime.now(UTC).isoformat()})
    event.notifications = attempts


@router.get("/contacts")
def contacts(patient=Depends(current_patient), db=Depends(get_db)):
    rows = db.scalars(select(EmergencyContact).where(
        EmergencyContact.patient_id == patient.id).order_by(EmergencyContact.priority)).all()
    return {"data": [public_contact(row) for row in rows]}


@router.post("/contacts")
def set_contact(body: ContactSetting, patient=Depends(current_patient), db=Depends(get_db)):
    relationship(db, body.relationship_id, patient_id=patient.id)
    row = db.scalar(select(EmergencyContact).where(
        EmergencyContact.relationship_id == body.relationship_id,
        EmergencyContact.patient_id == patient.id))
    if row is None:
        row = EmergencyContact(patient_id=patient.id, relationship_id=body.relationship_id)
        db.add(row)
    row.priority = body.priority
    row.enabled = body.enabled
    row.contact_name = body.contact_name
    db.commit()
    return {"data": public_contact(row)}


@router.post("/contacts/opt-in")
def opt_in(body: ContactOptIn, caregiver=Depends(current_patient), db=Depends(get_db)):
    rel = relationship(db, body.relationship_id, caregiver_user_id=caregiver.user_id)
    if not re.fullmatch(r"\+[1-9][0-9]{7,14}", body.phone):
        raise HTTPException(422, "Use an international phone number such as +15551234567")
    row = db.scalar(select(EmergencyContact).where(
        EmergencyContact.relationship_id == rel.id))
    if row is None:
        row = EmergencyContact(patient_id=rel.patient_id, relationship_id=rel.id)
        db.add(row)
    row.phone = body.phone if body.consent else None
    row.caregiver_opted_in = body.consent
    db.commit()
    return {"data": {"consenting": row.caregiver_opted_in,
                     "phone_last_four": row.phone[-4:] if row.phone else None}}


@router.post("/emergencies")
def start_emergency(body: EmergencyRequest, request: Request, patient=Depends(current_patient), db=Depends(get_db)):
    # Only an explicit user action calls this endpoint; it is never activated by ML screening.
    now = datetime.now(UTC)
    recent = db.scalars(select(EmergencyEvent).where(
        EmergencyEvent.patient_id == patient.id,
        EmergencyEvent.created_at > now - timedelta(seconds=45),
    )).all()
    if recent:
        raise HTTPException(429, "Emergency alert recently activated. Use the call emergency-services button now.")
    event = EmergencyEvent(patient_id=patient.id,
        status="activated", share_location=body.share_location,
        location=body.location if body.share_location else None,
        notifications=[])
    db.add(event); db.flush()
    notify(db, patient, event, 1, request.app.state.settings)
    db.commit()
    return {"data": public_event(event)}


@router.get("/emergencies")
def my_events(patient=Depends(current_patient), db=Depends(get_db)):
    events = db.scalars(select(EmergencyEvent).where(
        EmergencyEvent.patient_id == patient.id).order_by(EmergencyEvent.created_at.desc()).limit(20)).all()
    return {"data": [public_event(row) for row in events]}


@router.get("/caregiver/emergencies")
def caregiver_events(caregiver=Depends(current_patient), db=Depends(get_db)):
    rels = db.scalars(select(CaregiverRelationship).where(
        CaregiverRelationship.caregiver_user_id == caregiver.user_id,
        CaregiverRelationship.status == "active")).all()
    ids = [r.patient_id for r in rels if "alerts" in r.permissions and "emergency" in r.alert_severities]
    rows = db.scalars(select(EmergencyEvent).where(
        EmergencyEvent.patient_id.in_(ids)).order_by(EmergencyEvent.created_at.desc()).limit(20)).all() if ids else []
    return {"data": [{"patient_name": db.get(Patient, row.patient_id).display_name, **public_event(row)} for row in rows]}


@router.post("/caregiver/emergencies/{event_id}/acknowledge")
def acknowledge(event_id: str, caregiver=Depends(current_patient), db=Depends(get_db)):
    row = db.get(EmergencyEvent, event_id)
    if not row:
        raise HTTPException(404, "Alert not found")
    rel = db.scalar(select(CaregiverRelationship).where(
        CaregiverRelationship.patient_id == row.patient_id,
        CaregiverRelationship.caregiver_user_id == caregiver.user_id,
        CaregiverRelationship.status == "active"))
    if not rel or "alerts" not in rel.permissions or "emergency" not in rel.alert_severities:
        raise HTTPException(403, "Emergency alert access not authorized")
    if not row.acknowledged_at:
        row.acknowledged_by = caregiver.user_id
        row.acknowledged_at = datetime.now(UTC)
        row.status = "acknowledged"
        db.commit()
    return {"data": public_event(row)}


@router.post("/emergencies/{event_id}/escalate")
def escalate(event_id: str, request: Request, patient=Depends(current_patient), db=Depends(get_db)):
    row = db.scalar(select(EmergencyEvent).where(
        EmergencyEvent.id == event_id, EmergencyEvent.patient_id == patient.id))
    if not row:
        raise HTTPException(404, "Alert not found")
    if row.acknowledged_at:
        return {"data": public_event(row)}
    if datetime.now(UTC) - row.created_at.replace(tzinfo=row.created_at.tzinfo or UTC) < timedelta(minutes=2):
        raise HTTPException(409, "Secondary caregiver escalation becomes available after two minutes")
    if not row.escalation_at:
        row.escalation_at = datetime.now(UTC)
        notify(db, patient, row, 2, request.app.state.settings)
        db.commit()
    return {"data": public_event(row)}


@router.get("/notes")
def patient_notes(patient=Depends(current_patient), db=Depends(get_db)):
    rows = db.scalars(select(CaregiverNote).where(
        CaregiverNote.patient_id == patient.id).order_by(CaregiverNote.created_at.desc()).limit(50)).all()
    return {"data": [{"id": n.id, "body": n.body, "created_at": n.created_at.isoformat(),
                     "relationship_id": n.relationship_id, "author": "Caregiver"} for n in rows]}


@router.get("/caregiver/notes")
def caregiver_notes(caregiver=Depends(current_patient), db=Depends(get_db)):
    rels = db.scalars(select(CaregiverRelationship).where(
        CaregiverRelationship.caregiver_user_id == caregiver.user_id,
        CaregiverRelationship.status == "active")).all()
    ids = [r.id for r in rels]
    rows = db.scalars(select(CaregiverNote).where(
        CaregiverNote.relationship_id.in_(ids)).order_by(CaregiverNote.created_at.desc()).limit(50)).all() if ids else []
    return {"data": [{"id": n.id, "body": n.body, "created_at": n.created_at.isoformat(),
                     "relationship_id": n.relationship_id, "author": n.author_user_id == caregiver.user_id and "You" or "Patient"} for n in rows]}


@router.post("/caregiver/notes")
def write_note(body: CaregiverNoteInput, caregiver=Depends(current_patient), db=Depends(get_db)):
    rel = relationship(db, body.relationship_id, caregiver_user_id=caregiver.user_id)
    record = CaregiverNote(patient_id=rel.patient_id, relationship_id=rel.id,
        author_user_id=caregiver.user_id, body=body.body)
    db.add(record); db.commit()
    return {"data": {"id": record.id, "body": record.body}}


@router.get("/appointments")
def appointments(patient=Depends(current_patient), db=Depends(get_db)):
    rows = db.scalars(select(PatientAppointment).where(
        PatientAppointment.patient_id == patient.id).order_by(PatientAppointment.date_time).limit(50)).all()
    return {"data": [{"id": r.id, "date_time": r.date_time.isoformat(), "title": r.title,
                     "place": r.place, "notes": r.notes} for r in rows]}


@router.post("/appointments")
def add_appointment(body: AppointmentInput, patient=Depends(current_patient), db=Depends(get_db)):
    record = PatientAppointment(patient_id=patient.id,
        date_time=body.date_time.astimezone(UTC), title=body.title,
        place=body.place, notes=body.notes)
    db.add(record); db.commit()
    return {"data": {"id": record.id, "title": record.title}}


@router.get("/daily-briefing")
def daily_briefing(patient=Depends(current_patient), db=Depends(get_db)):
    day = datetime.now(ZoneInfo(patient.timezone)).date()
    summary = summaries.medication_summary(db, patient, day, day)
    checkin = db.scalar(select(Checkin).where(Checkin.patient_id == patient.id, Checkin.day == day))
    upcoming = db.scalars(select(PatientAppointment).where(
        PatientAppointment.patient_id == patient.id,
        PatientAppointment.date_time >= datetime.now(UTC)).order_by(
        PatientAppointment.date_time).limit(5)).all()
    return {"data": {"day": day.isoformat(), "patient_name": patient.display_name,
        "scheduled_doses": len(summary["today_doses"]),
        "doses_without_recorded_status": len(summary["unrecorded_doses"]),
        "checkin_recorded": checkin is not None,
        "upcoming_appointments": [{"date_time": a.date_time.isoformat(),
            "title": a.title} for a in upcoming],
        "message": "Review your actual discharge instructions; these are recorded tasks, not medical clearance."}}


@router.get("/visit-prep")
def visit_prep(patient=Depends(current_patient), db=Depends(get_db)):
    today = datetime.now(ZoneInfo(patient.timezone)).date()
    start = today - timedelta(days=6)
    rows = db.scalars(select(Checkin).where(Checkin.patient_id == patient.id,
        Checkin.day >= start).order_by(Checkin.day)).all()
    meds = db.scalars(select(Medication).where(
        Medication.patient_id == patient.id, Medication.active.is_(True))).all()
    med_ids = [m.id for m in meds]
    logs = db.scalars(select(MedicationLog).where(
        MedicationLog.medication_id.in_(med_ids),
        MedicationLog.recorded_at >= datetime.combine(start, datetime.min.time(), UTC)
    )).all() if med_ids else []
    questions = ["What activity restrictions apply to my procedure?",
                 "What symptoms should prompt me to contact the care team?",
                 "Should any medication instructions be clarified?"]
    return {"data": {"patient_name": patient.display_name,
        "from": start.isoformat(), "through": today.isoformat(),
        "checkins": [{"day": c.day.isoformat(), "pain": c.pain_level,
            "wellbeing": c.wellbeing, "activity_minutes": c.activity_minutes,
            "symptoms": c.symptoms, "note": c.note} for c in rows],
        "medications": [{"name": m.name, "dosage": m.dosage, "schedule": m.schedule} for m in meds],
        "dose_log_counts": {status: sum(1 for log in logs if log.status == status)
            for status in ("taken", "skipped", "missed")},
        "suggested_questions": questions,
        "notice": "Patient-entered or fictional demo information. Review accuracy before sharing. Not a clinical summary."}}
