"""Version-checked changes with immutable before/after audit snapshots."""
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select, update
from app.models import Medication, MedicationLog, Checkin, Alert, RecoveryAudit
from app.schemas import LogOut, CheckinOut, AlertOut
from app.services import risk


def cas(db, model, record, expected, values):
    result = db.execute(update(model).where(model.id == record.id, model.version == expected).values(**values, version=expected + 1).execution_options(synchronize_session=False))
    if result.rowcount != 1:
        raise HTTPException(409, "Record changed; reload before applying this correction")
    db.refresh(record)


def audit(db, patient, kind, record, action, reason, before, after):
    db.add(RecoveryAudit(patient_id=patient.id, actor_user_id=patient.user_id, resource_type=kind,
        resource_id=record.id, action=action, reason=reason, before=before, after=after))


def log_correction(db, patient, medication, log_id, body):
    record = db.scalar(select(MedicationLog).where(MedicationLog.id == str(log_id), MedicationLog.medication_id == medication.id))
    if record is None:
        raise HTTPException(404, "Log not found")
    before = LogOut.model_validate(record).model_dump(mode="json")
    old_units = (record.units_used or 0) if record.status == "taken" else 0
    new_units = (body.units_used or 0) if body.status == "taken" else 0
    delta = old_units - new_units
    if body.inventory_action == "adjust" and delta:
        if record.inventory_revision != medication.inventory_revision:
            raise HTTPException(409, "Inventory was manually reconciled after this log; reconcile the correction explicitly")
        result = db.execute(update(Medication).where(Medication.id == medication.id,
            Medication.inventory_revision == record.inventory_revision,
            Medication.supply_remaining.is_not(None), Medication.supply_remaining + delta >= 0
        ).values(supply_remaining=Medication.supply_remaining + delta))
        if result.rowcount != 1:
            raise HTTPException(409, "Inventory is unknown or insufficient for this correction")
    cas(db, MedicationLog, record, body.expected_version, {"status": body.status, "units_used": body.units_used,
        "inventory_revision": medication.inventory_revision})
    after = LogOut.model_validate(record).model_dump(mode="json")
    after["inventory_action"] = body.inventory_action
    audit(db, patient, "medication_log", record, "correct", body.reason, before, after)
    db.commit()
    return record


def checkin_correction(db, patient, record, body, settings):
    if body.observation.day != record.day:
        raise HTTPException(422, "Corrections cannot move a check-in to another day")
    before = CheckinOut.model_validate(record).model_dump(mode="json")
    cas(db, Checkin, record, body.expected_version, body.observation.model_dump())
    audit(db, patient, "checkin", record, "correct", body.reason, before, CheckinOut.model_validate(record).model_dump(mode="json"))
    risk.evaluate(db, record, settings)
    db.commit()
    return record


def alert_action(db, patient, record, body):
    before = AlertOut.model_validate(record).model_dump(mode="json")
    now = datetime.now(timezone.utc)
    if record.severity == "emergency" and body.action == "resolve" and not body.emergency_guidance_seen:
        raise HTTPException(422, "Read the emergency guidance before explicitly resolving this record; resolution is not a clinical clearance")
    if body.action == "acknowledge":
        if record.status != "open":
            raise HTTPException(409, "Only open alerts can be acknowledged")
        values = {"status": "acknowledged", "acknowledged_by": patient.user_id, "acknowledged_at": now}
    elif body.action == "resolve":
        if record.status == "resolved":
            raise HTTPException(409, "Alert is already resolved")
        values = {"status": "resolved", "resolved_by": patient.user_id, "resolved_at": now}
    else:
        values = {"status": "open", "resolved_by": None, "resolved_at": None, "acknowledged_by": None, "acknowledged_at": None}
    cas(db, Alert, record, body.expected_version, values)
    audit(db, patient, "alert", record, body.action, body.reason, before, AlertOut.model_validate(record).model_dump(mode="json"))
    db.commit()
    return record


def history(db, patient_id, kind, record_id, limit, offset):
    return db.scalars(select(RecoveryAudit).where(RecoveryAudit.patient_id == patient_id,
        RecoveryAudit.resource_type == kind, RecoveryAudit.resource_id == str(record_id)
    ).order_by(RecoveryAudit.created_at.desc(), RecoveryAudit.id).offset(offset).limit(limit)).all()
