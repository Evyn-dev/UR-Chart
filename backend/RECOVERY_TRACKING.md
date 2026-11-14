# Recovery Tracking (feature branch)

This is the **first implementation pass** for two UR Chart modules. It adds structured storage and read/write APIs, not a production clinical system. Use fictional data only.

## Setup

Follow the root `BACKEND_GUIDE.md`. From `backend/`, apply migrations with:

```powershell
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m pytest tests/test_recovery_tracking.py -q
.\.venv\Scripts\python -m uvicorn app.main:app --reload --no-access-log
```

## Medications

Existing `POST /api/medications` and `PATCH /api/medications/{id}` now support:

- `reminder_times`: optional array of local 24-hour times (e.g. `["08:00:00","20:00:00"]`), interpreted using the patient's IANA timezone
- `supply_remaining`: optional nonnegative manually entered unit count
- `refill_threshold`: optional nonnegative manually entered unit count

Example request:

```json
{
  "name": "Fictional medicine",
  "dosage": "Demonstration only",
  "schedule": "Per fictional discharge plan",
  "reminder_times": ["08:00:00", "20:00:00"],
  "supply_remaining": 4,
  "refill_threshold": 5
}
```

Additional read APIs, all authenticated and patient-scoped:

- `GET /api/medications/{id}/logs` lists recorded taken/skipped events
- `GET /api/medications/{id}/adherence` calculates the percentage **of logged events** marked taken; it cannot yet tell whether scheduled doses were missed
- `GET /api/medications/{id}/refill` reports a reminder flag when manually entered supply is less than or equal to the threshold; it does not request a prescription refill

This phase does **not** yet send actual notifications or decrement inventory automatically. Don't label stored reminder times as delivered reminders.

## Daily check-ins

Existing `POST /api/checkins` now accepts:

```json
{
  "day": "2026-11-13",
  "wellbeing": 3,
  "pain_level": 4,
  "symptoms": ["mild fatigue"],
  "activity_minutes": 12,
  "note": "Fictional recovery progress"
}
```

`pain_level` is optional (0–10), `symptoms` is an optional list of up to 20 free-text entries, and `activity_minutes` is optional (0–1440). `GET /api/checkins` returns them. One check-in per patient and day remains enforced. Symptoms are unstructured patient observations, **not validated clinical risk indicators**.

## Next phase

Develop clinician-reviewed risk rules, explicit escalation states, and a safe no-AI fallback separately. Add scheduled reminders, dose schedules, real missed-dose adherence, and optional notifications after confirming the team's integration contracts. No automatic medical diagnosis, clinical emergency monitoring, or care-team notification is implemented here.

## Collaboration

This work lives on `feature/recovery-tracking`; the main branch is unchanged until reviewed and merged. Team members should not independently modify the same migration or schema fields without coordinating. Run the existing test suite as well as the focused tests before merging.
