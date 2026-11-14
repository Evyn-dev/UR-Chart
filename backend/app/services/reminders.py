"""Patient-owned reminders with anchored local-time recurrence and versioned edits."""
from calendar import monthrange
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy import delete, select, update
from app.models.reminders import PersonalReminder


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def owned(db, patient_id, reminder_id):
    item = db.scalar(select(PersonalReminder).where(
        PersonalReminder.id == str(reminder_id), PersonalReminder.patient_id == patient_id))
    if item is None:
        raise HTTPException(404, "Reminder not found")
    return item


def resolve_wall_time(value, zone):
    # Fall-back overlaps use the first occurrence. Spring gaps move forward by
    # the DST gap (02:30 becomes 03:30); future days retain the original anchor.
    candidate = value.replace(tzinfo=zone, fold=0)
    return candidate.astimezone(timezone.utc)


def next_due(item, now):
    zone = ZoneInfo(item.timezone)
    anchor = utc(item.anchor_at).astimezone(zone).replace(tzinfo=None)
    after = max(utc(now), utc(item.due_at))
    local_after = after.astimezone(zone).replace(tzinfo=None)
    if item.repeat == "monthly":
        step = max(1, (local_after.year-anchor.year)*12 + local_after.month-anchor.month)
    else:
        days = max(1, (local_after.date()-anchor.date()).days)
        step = max(1, days//7) if item.repeat == "weekly" else days
    # Starting near `after` avoids iterating over years of missed occurrences.
    for _ in range(10):
        try:
            if item.repeat == "monthly":
                year, month0 = divmod(anchor.year*12+anchor.month-1+step, 12)
                candidate = anchor.replace(year=year, month=month0+1,
                    day=min(anchor.day, monthrange(year, month0+1)[1]))
            else:
                candidate = anchor + timedelta(days=step*(7 if item.repeat == "weekly" else 1))
            result = resolve_wall_time(candidate, zone)
        except (ValueError, OverflowError):
            break
        if result > after and (item.repeat != "weekdays" or candidate.weekday() < 5):
            return result
        step += 1
    raise HTTPException(422, "Unable to calculate next occurrence; edit the schedule")


def change(db, item, expected, values):
    result = db.execute(update(PersonalReminder).where(
        PersonalReminder.id == item.id, PersonalReminder.patient_id == item.patient_id,
        PersonalReminder.version == expected,
    ).values(**values, version=expected+1).execution_options(synchronize_session=False))
    if result.rowcount != 1:
        raise HTTPException(409, "Reminder changed; reload before retrying")
    db.commit()
    db.refresh(item)
    return item


def edit(db, item, body):
    values = body.model_dump(exclude={"expected_version"})
    values.update(due_at=utc(body.due_at), anchor_at=utc(body.due_at), last_action=None, last_action_at=None)
    return change(db, item, body.expected_version, values)


def apply_action(db, item, action, expected_version, now=None):
    now = utc(now or datetime.now(timezone.utc))
    if action == "delete":
        result = db.execute(delete(PersonalReminder).where(PersonalReminder.id == item.id,
            PersonalReminder.patient_id == item.patient_id, PersonalReminder.version == expected_version))
        if result.rowcount != 1:
            raise HTTPException(409, "Reminder changed; reload before retrying")
        db.commit()
        return None
    values = {"last_action": action, "last_action_at": now}
    if action == "toggle":
        values["active"] = not item.active
    else:
        if not item.active:
            raise HTTPException(409, "Reminder is inactive")
        if action == "snooze":
            if utc(item.due_at) > now:
                raise HTTPException(409, "Only due reminders can be snoozed")
            values["due_at"] = now + timedelta(minutes=10)
        elif action in {"complete", "dismiss"}:
            if item.repeat == "once":
                values["active"] = False
            else:
                values["due_at"] = next_due(item, now)
        else:
            raise HTTPException(422, "Unknown action")
    return change(db, item, expected_version, values)
