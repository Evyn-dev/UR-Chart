# Recovery tracking integration

Medication management, daily check-ins, prototype risk alerts, and caregiver sharing extend the existing shared backend. These APIs are integrated into `main`. Use fictional data only. See the [root README](../README.md) for current setup and the [branch inventory](../docs/REPOSITORY_CLEANUP.md) for unmerged work.

## Start and connect

From `backend/`, install `requirements-lock.txt` and configure demo credentials using [BACKEND_GUIDE.md](../BACKEND_GUIDE.md). Run:

```powershell
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m uvicorn app.main:app --reload --no-access-log
```

Swagger: `/docs`. OpenAPI: `/openapi.json`. All patient APIs use the existing bearer token and ownership checks, `{"data": ...}` successes, and `{"error": ...}` failures. Foreign record IDs return 404.

Teammates should configure the same reachable API base URL and separate demo tokens. Configure exact frontend origins in `ALLOWED_ORIGINS`. Separate localhost instances do not share data. Caregiver invitations currently support configured demo identities; this is not a production sharing system.

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

Legacy unlinked logs remain supported and visible but are not evidence of a scheduled dose. Unlinked writes are not idempotent; avoid automatic retries. Corrections and reversals use the versioned audit APIs documented below; hard deletion is not supported.

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

The supplied calendar day is stored as entered. Frontends should choose it in the patient's timezone. Historical days are allowed. Versioned corrections are documented below. `services/checkins.py` provides patient-scoped history/trends to other modules; use verified patient IDs. Trends omit missing values, report sample counts, and make no clinical interpretation.

## Prototype safety rules

New check-ins run through a separate deterministic service, without an LLM. Fetch `/{id}/risk` after submission and display its guidance/alerts. Preserve prototype labels. No matched rule does not mean safe.

Bundled `app/risk_rules.demo.json` is **prototype-only, not clinically validated**. Chest-pain and shortness-of-breath matches produce emergency guidance. `demo_urgent`, `demo_review`, and `demo_routine` exercise other display levels using synthetic codes. For possible immediate emergencies, guidance directs patients to emergency services (911 in the United States) without waiting for the app.

The educational warning-sign rationale is from the [American Heart Association](https://www.heart.org/health-topics/heart-attack/warning-signs-of-a-heart-attack). That source does not validate this software or replace clinician review.

No numeric clinical thresholds are bundled. The engine supports increase-over-prior-observation rules only with explicit parameters and review metadata. No validated trend rule has been supplied. Metadata records a review claim; maintainers must verify actual clinical approval outside the application.

Set `RISK_RULES_FILE` to a server-controlled JSON file for reviewed rules. Schema: `services/risk.py`. Increment rule version when definitions change. Never accept rules from patient requests. Prototype rules cannot evaluate in production.

Current symptoms are evaluated independently of prior wellbeing; an earlier normal check-in cannot suppress a match. Unknown positive codes, free-text symptoms, or notes receive an unassessed-observations alert. Free text is not clinically interpreted. Missing/invalid/empty/production-ineligible configuration persists an unavailable assessment with care-team and emergency guidance. No diagnosis, treatment, or dosage recommendation is generated.

Alerts are unique per check-in revision/rule/version. Evaluation audit records preserve the ruleset hash/snapshot and matched rules; alerts preserve triggering observations. Repeat processing is deduplicated in the service and database. Evaluations reflect history available at processing time; backfilled earlier check-ins do not automatically recompute later evaluations.

All notifications remain `not_sent`. No SMS, email, emergency dispatch, clinician escalation, or background monitoring exists. Do not imply anyone has been contacted.

## Database and tests

Migration `0003` follows existing `0002` without rewriting it. It adds schedule snapshots; dose links, timestamps, units and uniqueness; partial wellbeing, symptom reports and activity type; alert severity/evidence/rule identity/notification state; and risk evaluation audit records. Existing data is preserved. Downgrade refuses to invent wellbeing values for partial records. Coordinate shared migrations and back up first. PostgreSQL is not integration-tested.

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m alembic check
```

If Windows temporary-directory permissions fail, create `.test-tmp` and pass a fresh disposable `--basetemp=.test-tmp/unique-run-name`.

Original recovery baseline verified: **55 tests passed**, including shared tests, original recovery tests, populated migration preservation, schedule/timezone/DST behavior, inventory rollback, validation, isolation, risk classifications, emergency guidance, invalid-rule fallback, and production prototype rejection. Alembic reports no missing upgrade operations. One test-client dependency deprecation warning remains (httpx).

Deployment remains separate from publishing the source changes.


## Audited corrections and alert lifecycle

Every editable log, check-in, alert, and caregiver relationship exposes `version`. Send `expected_version` with changes. A stale version returns 409; reload instead of blindly retrying. Audit history records the authenticated actor, time, reason, and before/after values. Patient audit histories are private and not shared with caregivers.

| Method | Endpoint | Behavior |
|---|---|---|
| PATCH | `/api/medications/{id}/logs/{log_id}` | Correct status/units, or reverse with status `voided` |
| GET | `/api/medications/{id}/logs/{log_id}/audit` | Paginated correction history |
| GET | `/api/medications/summary` | Paginated active medications, today's doses/logs, unrecorded doses, refill warnings, adherence |
| PATCH | `/api/checkins/{id}` | Replace observations for the same day, retaining audit history |
| GET | `/api/checkins/{id}/audit` | Paginated check-in corrections |
| POST | `/api/alerts/{id}/actions` | Acknowledge, resolve, or reopen with audit |
| GET | `/api/alerts/{id}/audit` | Paginated alert lifecycle history |

Medication correction:

```json
{"expected_version":1,"status":"skipped","reason":"Accidentally selected taken","inventory_action":"adjust"}
```

This reverses the earlier confirmed unit deduction when inventory has not since been manually reconciled. For a corrected taken dose, explicitly include the corrected `units_used`; omitted units means unknown, not the old value. The log's scheduled occurrence and recorded time are immutable; to correct the wrong occurrence, void it and log the correct one. A voided occurrence remains reserved by its original log; restore it through another correction rather than inserting a duplicate.

If inventory was manually reconciled after logging, automatic correction returns 409. Reconcile the current physical count using medication PATCH, then explicitly use `inventory_action: "already_reconciled"`; this preserves the entered count and records the choice in the audit. Negative inventory is rejected. Stale edits roll back inventory and audit changes together.

Refill responses keep `actual_supply` (the recorded count, not independently verified) separate from `estimated_supply` (currently null). `estimated_days_remaining` is an optional projection using confirmed units recorded over the preceding 14 days, never assumed consumption from missing logs. Incomplete logging makes this estimate unreliable; it is not dosing advice. `status` is `unknown`, `refill_warning`, or `above_threshold`, with a patient-friendly message.

Adherence adds `overdue_unrecorded`: a due time has passed with no active log. This is a scheduling observation, not proof a dose was missed or a clinical threshold. Existing taken/skipped/confirmed-missed/unrecorded counts remain separate. Use optional start/end dates; history and timezone snapshots are preserved.

The medication summary accepts `start`, `end`, `limit` (1-50, default 20), and `offset`. `has_more` indicates additional active medications. Every summary and count applies to the returned medication page. It batches data into four SELECT queries rather than issuing queries for each medication. Today's completed records are non-voided logged events (including skipped/missed), not a claim all doses were taken.

Check-in correction uses a complete replacement observation with the same day:

```json
{"expected_version":1,"reason":"Corrected activity entry","observation":{"day":"2026-11-14","pain_level":2,"activity_minutes":15}}
```

Omitted optional observation fields are cleared. Corrections increment the version and reevaluate safety rules. Old alerts and evidence remain intact, including emergency alerts even when a corrected observation no longer matches. Repeat evaluation of the same revision/ruleset is deduplicated. A new revision may generate a new alert for the same rule, preventing an earlier resolved alert from hiding a newly reported concern.

Trends additionally return expected calendar days, recorded/missing days, consistency percent, and comparison of the two latest check-ins. Missing metric values are not imputed; descriptive values are not clinical predictions. Requested future dates count in the requested calendar window, so frontends should end consistency windows on or before the patient's current day.

Alert action:

```json
{"expected_version":1,"action":"acknowledge","reason":"Read the guidance"}
```

Actions record who and when. Resolving an emergency alert additionally requires `emergency_guidance_seen:true`. Resolution is a user workflow state, not clinical clearance or proof symptoms resolved. Emergency guidance remains visible. No correction or workflow action automatically dismisses emergency alerts, contacts a care team, or delivers a notification.

## Caregiver support

Use the existing demo identities. The patient specifies the intended caregiver's stable configured `DEMO_TOKENS` identity value, never a bearer token. An invitation can only be accepted or declined while authenticated as that recipient. No new authentication system or public identity directory is introduced.

| Method | Endpoint | Caller / purpose |
|---|---|---|
| POST | `/api/caregivers/invitations` | Patient invites a configured demo identity |
| GET | `/api/caregivers` | Patient lists relationships; optional status filter |
| PATCH | `/api/caregivers/{id}/permissions` | Patient changes permitted sections |
| POST | `/api/caregivers/{id}/revoke` | Patient immediately revokes pending/active access |
| GET | `/api/caregivers/{id}/audit` | Patient reviews consent/access events |
| GET | `/api/caregiver/invitations` | Caregiver's pending invitations |
| POST | `/api/caregiver/invitations/{id}/respond` | Intended recipient accepts or declines |
| GET | `/api/caregiver/relationships` | Caregiver's active relationships |
| GET | `/api/caregiver/relationships/{id}/dashboard` | Read-only permitted patient summary |

List/audit endpoints accept limit (1-100) and offset. Dashboard limit is 1-50 (default 20), with offset for medication and alert pages. Medication `has_more` and `alerts_has_more` indicate additional pages. Use relationship IDs from invitation/list responses, not arbitrary patient IDs.

Invite example:

```json
{"caregiver_user_id":"synthetic-jordan","permissions":["recovery_summary","medication_adherence","alerts"],"alert_severities":["urgent","emergency"]}
```

The response includes a relationship UUID, pending status, version 1, permissions, and timestamps. Creating an invitation does not grant access. The recipient accepts with:

```json
{"expected_version":1,"decision":"accept"}
```

The active relationship version then becomes 2. Patient revocation uses `{"expected_version":2}`. Reinviting a revoked/declined relationship requires fresh acceptance; an existing active/pending invitation returns 409 rather than silently changing consent. Permission changes also require the current version.

Permissions are independent:

| Permission | Shared information |
|---|---|
| `recovery_summary` | Seven-day check-in counts, whether today is recorded, missing check-in task |
| `medication_adherence` | Aggregate scheduled-dose counts and missing-record tasks for the medication page; no names, dosage, supply, or raw logs |
| `checkin_summary` | Seven-day wellbeing, pain, and activity values/trends; no notes, free-text symptoms, or detailed symptom reports |
| `alerts` | Only generated recovery alerts at patient-selected severities, with status, prototype label, and general safety guidance; no underlying evidence or free-text patient alerts |

A display name accompanies authorized dashboards. Omitted permissions produce omitted sections, not leaked null-filled medical records. Empty permissions deny dashboard access. Caregivers cannot modify medications, check-ins, alerts, consent, account settings, or chat. Shared care-team membership from the original foundation does not implicitly grant caregiver access.

Example restricted dashboard shape:

```json
{"data":{"relationship_id":"<UUID>","patient_display_name":"Synthetic Alex","permissions":["recovery_summary"],"recovery_summary":{"start":"2026-11-08","end":"2026-11-14","checkin_days":3,"expected_days":7,"checkin_recorded_today":true},"outstanding_tasks":[],"alerts_has_more":false,"alert_visibility":"not_authorized","notification_status":"not_sent"}}
```

Every read rechecks active consent and permissions. Revocation blocks subsequent reads immediately; the server also checks for changes before completing dashboard access and sends `Cache-Control: no-store`. It cannot recall data already viewed. Never persist shared patient data in frontend storage after revocation; clear the screen on 403/404.

Alerts distinguish `stored:true`, `visible_in_dashboard:true`, and `notification_status:"not_sent"`. Resolved emergency alerts remain visible if their severity is shared. No SMS, email, push, emergency dispatch, or automatic notification is delivered. Patient-selected alert visibility is not a substitute for emergency care.

Consent/access audits record invitation creation, acceptance/decline, access grant, permission change, revocation, and dashboard section views. They store actor IDs, relationship IDs, timestamps, and section namesâ€”not tokens or health content. Correction audits do contain necessary historical patient observations and remain patient-only.

## New migrations, verification, and limits

Migration `0004` adds recovery query indexes. `0005` adds consent/access and correction-audit tables, editable record versions, inventory reconciliation revisions, alert lifecycle fields, and per-check-in-revision rule uniqueness. Existing rows receive version 1. Applied migrations `0001`-`0003` are unchanged. Downgrade refuses to discard populated consent/correction history without explicit reconciliation.

Run `python -m alembic upgrade head` once on the shared database before starting the updated app; back it up first. No extra package or new secret is required. Existing demo token mappings, CORS origins, database URL, and prototype-rule configuration remain in use. The implementation is tested against SQLite; PostgreSQL migration/private-schema checks run in CI; load testing remains unperformed.

The feature adds no frontend, production login, delivered notifications, clinical validation, caregiver record editing, invitation email delivery, or automatic medication-consumption assumptions. Invitations do not expire automatically in this demo. Numeric rules still require actual clinician review outside the software. Teammates should use the same reachable backend URL and their own identities, and handle 409 by reloading versions.


Current verification results are recorded in the [cleanup report](../docs/REPOSITORY_CLEANUP.md#verification). Existing tests cover caregiver consent/scopes/revocation, cross-patient isolation, correction audits, stale-update rollback, supply estimates, repeated-rule revisions, fixed-query-count summaries, and populated migration upgrades.
