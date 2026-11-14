"""Bounded, patient-owned context for the existing chat provider boundary."""
import json
from sqlalchemy import select
from app.models import RecoveryPlan, Medication, Checkin, Alert
from app.services.ai import PatientContext


def patient_context(db, patient_id):
    instructions = db.scalars(select(RecoveryPlan.approved_instructions).where(
        RecoveryPlan.patient_id == patient_id, RecoveryPlan.approved_by.is_not(None)
    ).order_by(RecoveryPlan.created_at, RecoveryPlan.id).limit(10)).all()
    medications = db.scalars(select(Medication).where(
        Medication.patient_id == patient_id, Medication.active.is_(True)
    ).order_by(Medication.created_at.desc(), Medication.id).limit(10)).all()
    checkins = db.scalars(select(Checkin).where(Checkin.patient_id == patient_id)
        .order_by(Checkin.day.desc(), Checkin.id).limit(5)).all()
    alerts = db.scalars(select(Alert).where(Alert.patient_id == patient_id)
        .order_by(Alert.created_at.desc(), Alert.id).limit(5)).all()
    snapshot = {
        "active_medications": [{"name": m.name, "dosage_as_entered": m.dosage,
                                "schedule_as_entered": m.schedule} for m in medications],
        "recent_checkins": [{"day": c.day.isoformat(), "pain_level": c.pain_level,
                             "wellbeing": c.wellbeing, "symptoms_as_entered": c.symptoms} for c in checkins],
        "recent_alerts": [{"category": a.category, "severity": a.severity,
                           "status": a.status} for a in alerts],
    }
    return PatientContext(tuple(instructions), json.dumps(snapshot))
