"""Reminder recurrence and ownership rules. No background scheduler is implied."""
from datetime import datetime, timedelta, timezone
from calendar import monthrange
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy import select
from app.models.reminders import PersonalReminder


def owned(db, patient_id, reminder_id):
    item = db.scalar(select(PersonalReminder).where(
        PersonalReminder.id == str(reminder_id),
        PersonalReminder.patient_id == patient_id,
    ))
    if item is None:
        raise HTTPException(404, "Reminder not found")
    return item


def advance_local(value, frequency):
    if frequency == "daily":
        return value + timedelta(days=1)
    if frequency == "weekly":
        return value + timedelta(weeks=1)
    if frequency == "weekdays":
        candidate = value + timedelta(days=1)
        while candidate.weekday() >= 5:
            candidate += timedelta(days=1)
        return candidate
    if frequency == "monthly":
        year, month = value.year, value.month + 1
        if month == 13:
            year, month = year + 1, 1
        return value.replace(year=year, month=month, day=min(value.day, monthrange(year, month)[1]))
    raise ValueError("Unsupported recurrence")


def next_due(item, now):
    zone = ZoneInfo(item.timezone)
    previous = item.due_at
    if previous.tzinfo is None:
        previous = previous.replace(tzinfo=timezone.utc)
    local = previous.astimezone(zone)
    # The recurrence is based on local wall time and adjusts for DST.
    # Skip past occurrences without generating a backlog of notifications.
    for _ in range(3660):
        local = advance_local(local, item.repeat)
        if local.astimezone(timezone.utc) > now:
            return local.astimezone(timezone.utc)
    raise HTTPException(422, "Unable to calculate next occurrence")


def apply_action(db, item, action, now=None):
    now = now or datetime.now(timezone.utc)
    if action == "delete":
        db.delete(item)
        db.commit()
        return None
    if action == "toggle":
        item.active = not item.active
    elif action == "snooze":
        if not item.active:
            raise HTTPException(409, "Cannot snooze an inactive reminder")
        item.due_at = now + timedelta(minutes=10)
    elif action == "complete":
        if not item.active:
            raise HTTPException(409, "Reminder already inactive")
        if item.repeat == "once":
            item.active = False
        else:
            item.due_at = next_due(item, now)
    else:
        raise HTTPException(422, "Unknown action")
    db.commit()
    db.refresh(item)
    return item
