# Recovery tracking integration

Medication management, daily check-ins, and prototype risk alerts extend the shared backend on `feature/recovery-tracking`, PR #2. Use fictional data only. No frontend or chat implementation is changed.

## Start and connect

From `backend/`, install `requirements-lock.txt` and configure demo credentials using [BACKEND_GUIDE.md](../BACKEND_GUIDE.md). Run:

```powershell
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m uvicorn app.main:app --reload --no-access-log
```

Swagger: `/docs`. OpenAPI: `/openapi.json`. All patient APIs use the existing bearer token and ownership checks, `{"data": ...}` successes, and `{"error": ...}` failures. Foreign record IDs return 404.

Teammates should configure the same reachable API base URL and separate demo tokens. Configure exact frontend origins in `ALLOWED_ORIGINS`. Separate localhost instances do not share data. This branch is not deployed; production authentication remains outside this feature.

## Functional APIs

| Method | Path | Purpose |
|---|---|---|
| GET / POST | `/api/medications` | List/create medications |
| PATCH | `/api/medications/{id}` | Edit, reconcile supply, archive with `active:false` |
| POST | `/api/medications/{id}/log` | Record taken, skipped, or explicitly confirmed missed |
| GET | `/api/medications/{id}/logs` | Event history with limit/offset |
| GET | `/api/medications/{id}/schedules` | Historical schedules and timezones |
| GET | `/api/medications/{id}/doses` | Scheduled occurrences; required start/end dates |
| GET | `/api/medications/{id}/adherence` | Logged-event and scheduled-dose summaries |
| GET | `/api/medications/{id}/refill` | Supply and refill flag |
| GET / POST | `/api/checkins` | History or create check-in and evaluate rules |
| GET | `/api/checkins/{id}` | Individual check-in |
| GET | `/api/checkins/trends` | Descriptive trends; required start/end |
| GET | `/api/checkins/{id}/risk` | Stored assessment, alerts, and guidance |
| POST | `/api/checkins/{id}/evaluate` | Idempotent evaluation using current server rules |
| GET | `/api/alerts` | Patient-visible alerts and rule evidence |

Use `start=YYYY-MM-DD&end=YYYY-MM-DD`. Windows are inclusive, at most 93 days. Check-in history supports optional start/end plus limit/offset and sorts by reported day.

## Medication integration

Example POST:

```json
{"name":"Fictional medicine","dosage":"Patient-entered demo dose","schedule":"Patient-entered daily schedule","reminder_times":["08:00","20:00"],"supply_remaining":10,"refill_threshold":3}
```

Reminder times explicitly describe a daily schedule: up to 12 unique local minute-level times. Empty times mean no expectations. Dosage/schedule text is never parsed to invent doses. PRN/weekly schedules, fractional inventory units, and actual reminder delivery are not implemented.

Set the patient's IANA timezone using `PATCH /api/patients/me`. Creating/editing reminder times, archiving/reactivating, or changing the patient's timezone creates/closes effective schedule intervals. Past expectations retain their original timezone. New schedules begin at the change time, without retroactive doses. Existing reminders are initialized at migration time, not original medication creation time.

Daylight-saving gaps/repeated times produce `schedule_issues`; they are never silently moved or duplicated. Resolve intended times with the care team; this API does not recommend dosing times.

Retrieve `/doses` before logging. Supply its exact `schedule_id` and `scheduled_for`:

```json
{"status":"taken","recorded_at":"2026-11-13T21:05:00Z","schedule_id":"<returned UUID>","scheduled_for":"<returned UTC timestamp>","units_used":1}
```

Only due, unambiguous occurrences can be linked. Duplicate scheduled-dose logs return 409 without consuming inventory twice. `units_used` is optional and explicitly patient-entered; it is never inferred from dosage text. Supply decreases only for a taken event with units_used. Unknown/insufficient inventory returns 409. Skipped/missed events cannot consume units.

Legacy unlinked logs remain supported and visible but are not evidence of a scheduled dose. Unlinked writes are not idempotent; avoid automatic retries. Log corrections/deletion are not implemented.

Adherence:

- `expected_due`: known scheduled occurrences due by server time in the window.
- `scheduled_taken`, `scheduled_skipped`, `confirmed_missed`, `unrecorded`: separate counts.
- `scheduled_adherence_percent`: taken / expected_due x 100; null with no denominator or unresolved schedule issues.
- `adherence_percent`, `taken`, `skipped`, `total_logged`: legacy all-time logged-event statistics retained for compatibility.

**Unrecorded means unknown, not confirmed missed.** Display separate counts and do not describe this calculation as a clinical assessment. The default window is the patient's current day and preceding 29 days. Future occurrences do not enter the denominator.

Refill status is true when known supply is at/below the user-entered threshold; null means unknown. PATCH can clear either field with null. This flag does not contact a pharmacy or request a prescription.

## Check-ins and reusable services

Example partial check-in:

```json
{"day":"2026-11-13","pain_level":4,"symptom_reports":[{"code":"chest_pain","present":true}],"activity_minutes":12,"activity_type":"walking","note":"Fictional demonstration"}
```

Wellbeing (1-5), pain (0-10), activity minutes (0-1440), notes, and symptoms are optional; at least one observation is required. One check-in per patient/day remains enforced. Structured symptoms have unique codes, present/absent, optional mild/moderate/severe severity, and descriptions. Legacy free-text `symptoms` remains compatible.

The supplied calendar day is stored as entered. Frontends should choose it in the patient's timezone. Historical days are allowed; edits are not implemented. `services/checkins.py` provides patient-scoped history/trends to other modules; use verified patient IDs. Trends omit missing values, report sample counts, and make no clinical interpretation.

## Prototype safety rules

New check-ins run through a separate deterministic service, without an LLM. Fetch `/{id}/risk` after submission and display its guidance/alerts. Preserve prototype labels. No matched rule does not mean safe.

Bundled `app/risk_rules.demo.json` is **prototype-only, not clinically validated**. Chest-pain and shortness-of-breath matches produce emergency guidance. `demo_urgent`, `demo_review`, and `demo_routine` exercise other display levels using synthetic codes. For possible immediate emergencies, guidance directs patients to emergency services (911 in the United States) without waiting for the app.

The educational warning-sign rationale is from the [American Heart Association](https://www.heart.org/health-topics/heart-attack/warning-signs-of-a-heart-attack). That source does not validate this software or replace clinician review.

No numeric clinical thresholds are bundled. The engine supports increase-over-prior-observation rules only with explicit parameters and review metadata. No validated trend rule has been supplied. Metadata records a review claim; maintainers must verify actual clinical approval outside the application.

Set `RISK_RULES_FILE` to a server-controlled JSON file for reviewed rules. Schema: `services/risk.py`. Increment rule version when definitions change. Never accept rules from patient requests. Prototype rules cannot evaluate in production.

Current symptoms are evaluated independently of prior wellbeing; an earlier normal check-in cannot suppress a match. Unknown positive codes, free-text symptoms, or notes receive an unassessed-observations alert. Free text is not clinically interpreted. Missing/invalid/empty/production-ineligible configuration persists an unavailable assessment with care-team and emergency guidance. No diagnosis, treatment, or dosage recommendation is generated.

Alerts are unique per check-in/rule/version. Evaluation audit records preserve the ruleset hash/snapshot and matched rules; alerts preserve triggering observations. Repeat processing is deduplicated in the service and database. Evaluations reflect history available at processing time; backfilled earlier check-ins do not automatically recompute later evaluations.

All notifications remain `not_sent`. No SMS, email, emergency dispatch, clinician escalation, or background monitoring exists. Do not imply anyone has been contacted.

## Database and tests

Migration `0003` follows existing `0002` without rewriting it. It adds schedule snapshots; dose links, timestamps, units and uniqueness; partial wellbeing, symptom reports and activity type; alert severity/evidence/rule identity/notification state; and risk evaluation audit records. Existing data is preserved. Downgrade refuses to invent wellbeing values for partial records. Coordinate shared migrations and back up first. PostgreSQL is not integration-tested.

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m alembic check
```

If Windows temporary-directory permissions fail, create `.test-tmp` and pass a fresh disposable `--basetemp=.test-tmp/unique-run-name`.

Verified: **55 tests passed**, including shared tests, original recovery tests, populated migration preservation, schedule/timezone/DST behavior, inventory rollback, validation, isolation, risk classifications, emergency guidance, invalid-rule fallback, and production prototype rejection. Alembic reports no missing upgrade operations. One test-client dependency deprecation warning remains (httpx).

The branch stays a draft for team review. No merge or deployment is performed.
