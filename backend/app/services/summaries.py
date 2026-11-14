"""Batch medication summaries: query count does not grow per medication."""
from collections import defaultdict
from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import select, func, or_
from app.models import Medication, MedicationSchedule, MedicationLog
from app.schemas import MedicationOut, LogOut
from app.services import medications


def refill_status(medication, confirmed_units=0, observation_days=14):
    supply, threshold = medication.supply_remaining, medication.refill_threshold
    needed = supply <= threshold if supply is not None and threshold is not None else None
    status = "unknown" if needed is None else "refill_warning" if needed else "above_threshold"
    message = {"unknown": "Enter your current supply and warning threshold to check refill status.",
        "refill_warning": "Your recorded supply is at or below your refill warning threshold. Contact your pharmacy or care team about a refill.",
        "above_threshold": "Your recorded supply is above your refill warning threshold."}[status]
    estimate = round(supply / (confirmed_units / observation_days), 1) if supply is not None and confirmed_units > 0 else None
    return {"medication_id": medication.id, "supply_remaining": supply, "actual_supply": supply,
        "estimated_supply": None, "estimated_days_remaining": estimate, "refill_threshold": threshold,
        "refill_needed": needed, "status": status, "message": message,
        "note": "Actual supply changes only from entered counts and confirmed units. Days remaining is an estimate from 14 days of recorded consumption, not dosing advice or a pharmacy request."}


def refill(db, medication, at=None):
    at = at or datetime.now(timezone.utc)
    units = db.scalar(select(func.sum(MedicationLog.units_used)).where(MedicationLog.medication_id == medication.id,
        MedicationLog.status == "taken", MedicationLog.recorded_at >= at - timedelta(days=14), MedicationLog.recorded_at <= at)) or 0
    return refill_status(medication, units)


def medication_summary(db, patient, start=None, end=None, limit=20, offset=0, at=None):
    at = at or datetime.now(timezone.utc)
    today = at.astimezone(ZoneInfo(patient.timezone)).date()
    end = end or today
    start = start or end - timedelta(days=29)
    medications.date_window(start, end)
    rows = db.scalars(select(Medication).where(Medication.patient_id == patient.id, Medication.active.is_(True))
        .order_by(Medication.created_at, Medication.id).offset(offset).limit(limit + 1)).all()
    has_more, rows = len(rows) > limit, rows[:limit]
    ids = [row.id for row in rows]
    result = {"medications": [], "today": today, "today_doses": [], "completed_records": [], "unrecorded_doses": [], "refill_warnings": [],
        "adherence": {}, "limit": limit, "offset": offset, "has_more": has_more, "start": start, "end": end}
    if not ids:
        return result
    lower = datetime.combine(min(start, today), time.min, timezone.utc) - timedelta(days=1)
    upper = datetime.combine(max(end, today) + timedelta(days=2), time.min, timezone.utc)
    schedules = db.scalars(select(MedicationSchedule).where(MedicationSchedule.medication_id.in_(ids),
        MedicationSchedule.effective_from < upper, or_(MedicationSchedule.effective_until.is_(None), MedicationSchedule.effective_until > lower))).all()
    logs = db.scalars(select(MedicationLog).where(MedicationLog.medication_id.in_(ids),
        or_(MedicationLog.scheduled_for.between(lower, upper), MedicationLog.recorded_at.between(min(lower, at - timedelta(days=14)), upper)))).all()
    grouped = db.execute(select(MedicationLog.medication_id, MedicationLog.status, func.count()).where(MedicationLog.medication_id.in_(ids),
        MedicationLog.status != "voided").group_by(MedicationLog.medication_id, MedicationLog.status)).all()
    schedule_map, log_map, counts = defaultdict(list), defaultdict(list), defaultdict(dict)
    for row in schedules:
        schedule_map[row.medication_id].append(row)
    for row in logs:
        log_map[row.medication_id].append(row)
    for med_id, status, count in grouped:
        counts[med_id][status] = count
    for med in rows:
        med_logs = log_map[med.id]
        result["medications"].append(MedicationOut.model_validate(med))
        doses = medications.dose_history(db, med, today, today, at, schedule_map[med.id], med_logs)
        result["today_doses"].extend({**dose, "medication_id": med.id} for dose in doses["doses"])
        result["unrecorded_doses"].extend({**dose, "medication_id": med.id} for dose in doses["doses"] if dose["status"] == "unrecorded")
        result["completed_records"].extend(LogOut.model_validate(log) for log in med_logs if log.status != "voided" and medications.utc(log.recorded_at).astimezone(ZoneInfo(patient.timezone)).date() == today)
        units = sum(log.units_used or 0 for log in med_logs if log.status == "taken" and at - timedelta(days=14) <= medications.utc(log.recorded_at) <= at)
        refill_data = refill_status(med, units)
        if refill_data["refill_needed"]:
            result["refill_warnings"].append(refill_data)
        result["adherence"][med.id] = medications.adherence(db, med, start, end, at, schedule_map[med.id], med_logs, counts[med.id])
    return result
