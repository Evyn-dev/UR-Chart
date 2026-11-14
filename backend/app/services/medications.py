"""Daily schedules are explicit patient input, never inferred from dose text."""
from datetime import datetime, date, time, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy import select, update, func, or_
from app.models import MedicationSchedule, MedicationLog, Medication


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def date_window(start, end):
    if end < start or (end - start).days > 92:
        raise HTTPException(422, "Date range must be ordered and at most 93 days")


def replace_schedule(db, medication, patient_timezone, at=None):
    at = at or datetime.now(timezone.utc)
    db.execute(update(MedicationSchedule).where(MedicationSchedule.medication_id == medication.id, MedicationSchedule.effective_until.is_(None)).values(effective_until=at))
    if medication.active and medication.reminder_times:
        db.add(MedicationSchedule(medication_id=medication.id, timezone=patient_timezone, reminder_times=list(medication.reminder_times), effective_from=at))
    db.flush()


def occurrences(schedule, start, end):
    """Exclude DST gaps/ambiguities, reporting them for explicit clarification."""
    zone = ZoneInfo(schedule.timezone)
    day = max(start, utc(schedule.effective_from).astimezone(zone).date())
    if schedule.effective_until is not None:
        end = min(end, utc(schedule.effective_until).astimezone(zone).date())
    while day <= end:
        for local_time in schedule.reminder_times:
            wall = datetime.combine(day, time.fromisoformat(local_time))
            candidates = {wall.replace(tzinfo=zone, fold=fold).astimezone(timezone.utc) for fold in (0, 1)
                          if wall.replace(tzinfo=zone, fold=fold).astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == wall}
            relevant = [dt for dt in candidates if dt >= utc(schedule.effective_from) and (schedule.effective_until is None or dt < utc(schedule.effective_until))]
            if len(candidates) != 1:
                local_start = utc(schedule.effective_from).astimezone(zone).replace(tzinfo=None)
                local_end = utc(schedule.effective_until).astimezone(zone).replace(tzinfo=None) if schedule.effective_until else datetime.max
                if relevant or (not candidates and local_start <= wall < local_end):
                    yield {"issue": "ambiguous_local_time" if candidates else "nonexistent_local_time", "local_day": day.isoformat(), "local_time": local_time, "timezone": schedule.timezone, "schedule_id": schedule.id}
            elif relevant:
                yield {"schedule_id": schedule.id, "scheduled_for": relevant[0], "local_day": day, "local_time": local_time, "timezone": schedule.timezone}
        day += timedelta(days=1)


def dose_history(db, medication, start, end, at=None, schedules=None, logs=None):
    date_window(start, end)
    at = at or datetime.now(timezone.utc)
    lower = datetime.combine(start, time.min, timezone.utc) - timedelta(days=1)
    upper = datetime.combine(end + timedelta(days=2), time.min, timezone.utc)
    schedules = schedules if schedules is not None else db.scalars(select(MedicationSchedule).where(
        MedicationSchedule.medication_id == medication.id,
        MedicationSchedule.effective_from < upper,
        or_(MedicationSchedule.effective_until.is_(None), MedicationSchedule.effective_until > lower))).all()
    # Bound log reads by UTC margins around all possible local-day offsets.
    logs = logs if logs is not None else db.scalars(select(MedicationLog).where(MedicationLog.medication_id == medication.id,
        MedicationLog.scheduled_for >= datetime.combine(start, time.min, timezone.utc) - timedelta(days=1),
        MedicationLog.scheduled_for < datetime.combine(end + timedelta(days=2), time.min, timezone.utc))).all()
    by_time = {utc(log.scheduled_for): log for log in logs if log.status != "voided" and log.scheduled_for is not None}
    doses, issues = [], []
    for schedule in schedules:
        for item in occurrences(schedule, start, end):
            if "issue" in item:
                issues.append(item)
            else:
                log = by_time.get(item["scheduled_for"])
                doses.append({**item, "status": log.status if log else "unrecorded", "log_id": log.id if log else None, "overdue": item["scheduled_for"] < at and log is None, "due": item["scheduled_for"] <= at})
    doses.sort(key=lambda d: d["scheduled_for"])
    return {"doses": doses, "schedule_issues": issues}


def log_dose(db, medication, body, at=None):
    at = at or datetime.now(timezone.utc)
    if body.recorded_at > at:
        raise HTTPException(422, "Cannot record a future dose event")
    if body.schedule_id:
        schedule = db.scalar(select(MedicationSchedule).where(MedicationSchedule.id == str(body.schedule_id), MedicationSchedule.medication_id == medication.id))
        if schedule is None:
            raise HTTPException(404, "Schedule not found")
        day = body.scheduled_for.astimezone(ZoneInfo(schedule.timezone)).date()
        if body.scheduled_for > at or not any(item.get("scheduled_for") == body.scheduled_for for item in occurrences(schedule, day, day)):
            raise HTTPException(422, "Dose must match an unambiguous due scheduled occurrence")
    if body.units_used is not None:
        # Conditional update prevents two requests from consuming the same inventory.
        result = db.execute(update(Medication).where(Medication.id == medication.id,
            Medication.inventory_revision == medication.inventory_revision,
            Medication.supply_remaining >= body.units_used).values(supply_remaining=Medication.supply_remaining - body.units_used))
        if result.rowcount != 1:
            raise HTTPException(409, "Supply unknown or insufficient; reconcile inventory before logging units_used")
    values = body.model_dump()
    values["schedule_id"] = str(body.schedule_id) if body.schedule_id else None
    record = MedicationLog(medication_id=medication.id, inventory_revision=medication.inventory_revision, **values)
    db.add(record)
    db.commit()  # duplicate scheduled dose rolls back its inventory update too
    db.refresh(record)
    return record


def adherence(db, medication, start, end, at=None, schedules=None, logs=None, legacy=None):
    history = dose_history(db, medication, start, end, at, schedules, logs)
    due = [d for d in history["doses"] if d["due"]]
    counts = {status: sum(d["status"] == status for d in due) for status in ("taken", "skipped", "missed", "unrecorded")}
    legacy = legacy if legacy is not None else dict(db.execute(select(MedicationLog.status, func.count()).where(MedicationLog.medication_id == medication.id, MedicationLog.status != "voided").group_by(MedicationLog.status)).all())
    taken, skipped = legacy.get("taken", 0), legacy.get("skipped", 0)
    total = sum(legacy.values())
    return {"taken": taken, "skipped": skipped, "total_logged": total,
        "adherence_percent": round(100 * taken / total, 1) if total else None,
        "overdue_unrecorded": sum(d["overdue"] for d in due), "expected_due": len(due), "scheduled_taken": counts["taken"], "scheduled_skipped": counts["skipped"],
        "confirmed_missed": counts["missed"], "unrecorded": counts["unrecorded"],
        "scheduled_adherence_percent": round(100 * counts["taken"] / len(due), 1) if due and not history["schedule_issues"] else None,
        "schedule_issues": history["schedule_issues"]}
