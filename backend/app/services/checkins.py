"""Patient-scoped access for other modules; callers supply verified patient IDs."""
from sqlalchemy import select
from app.models import Checkin
from app.services.medications import date_window


def history(db, patient_id, start=None, end=None, limit=50, offset=0):
    query = select(Checkin).where(Checkin.patient_id == patient_id)
    if start and end:
        date_window(start, end)
    if start:
        query = query.where(Checkin.day >= start)
    if end:
        query = query.where(Checkin.day <= end)
    return db.scalars(query.order_by(Checkin.day.desc(), Checkin.id).offset(offset).limit(limit)).all()


def trends(db, patient_id, start, end, rows=None):
    date_window(start, end)
    rows = list(reversed(rows if rows is not None else history(db, patient_id, start, end, limit=93)))
    counts, averages, changes = {}, {}, {}
    for field in ("wellbeing", "pain_level", "activity_minutes"):
        values = [getattr(row, field) for row in rows if getattr(row, field) is not None]
        counts[field] = len(values)
        averages[field] = round(sum(values) / len(values), 2) if values else None
        changes[field] = values[-1] - values[0] if len(values) >= 2 else None
    expected = (end - start).days + 1
    comparison = {}
    if len(rows) >= 2:
        comparison = {"previous_day": rows[-2].day.isoformat(), "latest_day": rows[-1].day.isoformat(), "changes": {
            field: getattr(rows[-1], field) - getattr(rows[-2], field) if getattr(rows[-1], field) is not None and getattr(rows[-2], field) is not None else None
            for field in ("wellbeing", "pain_level", "activity_minutes")}}
    return {"expected_days": expected, "missing_days": expected - len(rows), "consistency_percent": round(100 * len(rows) / expected, 1), "latest_comparison": comparison, "days_recorded": len(rows), "metric_counts": counts, "averages": averages, "first_to_last_change": changes}
