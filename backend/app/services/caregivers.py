"""Patient-authorized, read-only sharing. Never delegates the patient's identity."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy import select, update, case
from app.models import Patient, Checkin, Alert, CaregiverRelationship, CaregiverAudit
from app.services import checkins, summaries
from app.services.risk import EMERGENCY_GUIDANCE, FALLBACK_GUIDANCE


def event(db, relationship, actor, action, details=None):
    db.add(CaregiverAudit(patient_id=relationship.patient_id, relationship_id=relationship.id,
        actor_user_id=actor.user_id, action=action, details=details or {}))


def transition(db, relationship, expected, allowed, values):
    result = db.execute(update(CaregiverRelationship).where(CaregiverRelationship.id == relationship.id,
        CaregiverRelationship.version == expected, CaregiverRelationship.status.in_(allowed)
    ).values(**values, version=expected + 1).execution_options(synchronize_session=False))
    if result.rowcount != 1:
        raise HTTPException(409, "Relationship changed; reload its current status")
    db.refresh(relationship)


def invite(db, patient, body, settings):
    if body.caregiver_user_id == patient.user_id:
        raise HTTPException(422, "Cannot invite yourself")
    valid_identities = set(settings.demo_tokens.values())
    if settings.hosted_demo_code_hash:
        valid_identities.add("synthetic-demo-caregiver")
    if body.caregiver_user_id not in valid_identities:
        raise HTTPException(422, "Recipient must be a configured demo identity")
    record = db.scalar(select(CaregiverRelationship).where(CaregiverRelationship.patient_id == patient.id,
        CaregiverRelationship.caregiver_user_id == body.caregiver_user_id))
    values = body.model_dump()
    if record:
        transition(db, record, record.version, ["declined", "revoked"], {**values, "status": "pending", "responded_at": None, "revoked_at": None})
    else:
        record = CaregiverRelationship(patient_id=patient.id, **values)
        db.add(record)
        db.flush()
    event(db, record, patient, "invitation_created", {"permissions": record.permissions, "alert_severities": record.alert_severities})
    db.commit()
    return record


def owner_record(db, patient, id):
    record = db.scalar(select(CaregiverRelationship).where(CaregiverRelationship.id == str(id), CaregiverRelationship.patient_id == patient.id))
    if record is None:
        raise HTTPException(404, "Relationship not found")
    return record


def respond(db, caregiver, id, body):
    record = db.scalar(select(CaregiverRelationship).where(CaregiverRelationship.id == str(id), CaregiverRelationship.caregiver_user_id == caregiver.user_id))
    if record is None:
        raise HTTPException(404, "Invitation not found")
    status = "active" if body.decision == "accept" else "declined"
    transition(db, record, body.expected_version, ["pending"], {"status": status, "responded_at": datetime.now(timezone.utc)})
    event(db, record, caregiver, "invitation_accepted" if status == "active" else "invitation_declined")
    if status == "active":
        event(db, record, caregiver, "access_granted", {"permissions": record.permissions, "alert_severities": record.alert_severities})
    db.commit()
    return record


def change_permissions(db, patient, id, body):
    record = owner_record(db, patient, id)
    before = {"permissions": record.permissions, "alert_severities": record.alert_severities}
    transition(db, record, body.expected_version, ["pending", "active"], body.model_dump(exclude={"expected_version"}))
    event(db, record, patient, "permissions_changed", {"before": before, "after": {"permissions": record.permissions, "alert_severities": record.alert_severities}})
    db.commit()
    return record


def revoke(db, patient, id, body):
    record = owner_record(db, patient, id)
    transition(db, record, body.expected_version, ["pending", "active"], {"status": "revoked", "revoked_at": datetime.now(timezone.utc)})
    event(db, record, patient, "access_revoked")
    db.commit()
    return record


def dashboard(db, caregiver, id, limit=20, offset=0):
    relationship = db.scalar(select(CaregiverRelationship).where(CaregiverRelationship.id == str(id),
        CaregiverRelationship.caregiver_user_id == caregiver.user_id, CaregiverRelationship.status == "active"))
    if relationship is None:
        raise HTTPException(404, "Active relationship not found")
    if not relationship.permissions:
        raise HTTPException(403, "Patient has not shared any dashboard sections")
    patient = db.get(Patient, relationship.patient_id)
    permissions = set(relationship.permissions)
    today = datetime.now(ZoneInfo(patient.timezone)).date()
    start = today - timedelta(days=6)
    result = {"relationship_id": relationship.id, "patient_display_name": patient.display_name,
        "permissions": relationship.permissions, "alert_visibility": "not_authorized", "notification_status": "not_sent"}
    tasks = []
    rows = checkins.history(db, patient.id, start, today, limit=7) if permissions & {"recovery_summary", "checkin_summary"} else []
    if "recovery_summary" in permissions:
        done_today = any(row.day == today for row in rows)
        result["recovery_summary"] = {"start": start, "end": today, "checkin_days": len(rows), "expected_days": 7, "checkin_recorded_today": done_today}
        if not done_today:
            tasks.append({"type": "checkin", "description": "No check-in recorded today; this is not evidence of a health problem."})
    if "checkin_summary" in permissions:
        checkin_rows = checkins.history(db, patient.id, start, today, limit=limit, offset=offset)
        result["checkin_summary"] = {
            "trends": checkins.trends(db, patient.id, start, today, checkin_rows),
            "recent": [{
                "id": row.id, "day": row.day, "wellbeing": row.wellbeing,
                "pain_level": row.pain_level, "activity_minutes": row.activity_minutes,
                "activity_type": row.activity_type, "symptoms": row.symptoms,
                "symptom_reports": row.symptom_reports, "note": row.note,
            } for row in checkin_rows],
            "offset": offset, "limit": limit,
            "has_more": len(checkin_rows) == limit,
        }
    if "medication_adherence" in permissions:
        summary = summaries.medication_summary(db, patient, start, today, limit, offset)
        fields = ("expected_due", "scheduled_taken", "scheduled_skipped", "confirmed_missed", "unrecorded", "overdue_unrecorded")
        result["medication_adherence"] = {
            "start": start, "end": today, "counts": {
                field: sum(value[field] for value in summary["adherence"].values()) for field in fields},
            "medications": summary["medications"],
            "adherence_by_medication": summary["adherence"],
            "today_doses": summary["today_doses"],
            "completed_records": summary["completed_records"],
            "unrecorded_doses": summary["unrecorded_doses"],
            "refill_warnings": summary["refill_warnings"],
            "medications_included": len(summary["medications"]),
            "has_more": summary["has_more"], "offset": offset, "limit": limit,
            "schedule_issue_count": sum(len(v["schedule_issues"]) for v in summary["adherence"].values()),
        }
        count = sum(d["due"] for d in summary["unrecorded_doses"])
        if count:
            tasks.append({"type": "dose_record", "count": count, "description": "Scheduled doses have no recorded status. This does not prove they were missed."})
    if "alerts" in permissions:
        alerts = db.scalars(select(Alert).where(Alert.patient_id == patient.id, Alert.category == "recovery_safety",
            Alert.severity.in_(relationship.alert_severities)).order_by(
            case((Alert.severity == "emergency", 0), (Alert.severity == "urgent", 1), else_=2), Alert.created_at.desc(), Alert.id
        ).offset(offset).limit(limit + 1)).all()
        result["alerts_has_more"] = len(alerts) > limit
        result["alerts"] = [{"id": row.id, "severity": row.severity, "status": row.status, "prototype_only": row.prototype_only,
            "guidance": EMERGENCY_GUIDANCE if row.severity == "emergency" else FALLBACK_GUIDANCE,
            "stored": True, "visible_in_dashboard": True, "notification_status": row.notification_status} for row in alerts[:limit]]
        result["alert_visibility"] = "patient_selected_severities"
    result["outstanding_tasks"] = tasks
    # Serialize access against a concurrent revoke/permission change before returning data.
    guard = db.execute(update(CaregiverRelationship).where(CaregiverRelationship.id == relationship.id,
        CaregiverRelationship.version == relationship.version, CaregiverRelationship.status == "active"
    ).values(updated_at=relationship.updated_at))
    if guard.rowcount != 1:
        raise HTTPException(404, "Access changed; request the dashboard again")
    event(db, relationship, caregiver, "dashboard_viewed", {"sections": sorted(permissions)})
    db.commit()
    return result
