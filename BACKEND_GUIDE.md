# UR Chart shared backend guide

For medication schedules, scheduled-dose adherence, partial check-ins, trends, and prototype risk alerts, see [Recovery Tracking](backend/RECOVERY_TRACKING.md), which documents the additive contracts after this foundation.

Use fictional data only. This is the specialized API integration reference. The [root README](README.md) is authoritative for current setup, authentication modes, deployment, and limitations.

## 1. Install and configure

Follow [local setup and configuration](README.md#local-setup) in the root README.

## 2. Initialize the database and start

```powershell
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m app.seed
.\.venv\Scripts\python -m uvicorn app.main:app --reload --no-access-log
```

Open `/docs` for Swagger or `/openapi.json` for the API schema. In Swagger's **Authorize** dialog, enter the generated token. `/api/health` is public and verifies the migration revision. If migrations are missing it returns 503. Authentication and AI configuration status are reported separately from database health.

The app does not migrate automatically on startup: one designated developer runs migrations before starting shared workers. SQLite is stored at `backend/urchart.db` when launched from `backend/`. Foreign keys are enabled and writes have a five-second busy timeout. SQLite is suitable for a small single-process demo, not concurrent multi-host storage.

## 3. Frontend integration

Keep the API base URL in frontend configuration (for example `VITE_API_BASE_URL`). Supply a token at runtime through your demo login/dev tooling; do not embed it in committed JavaScript or public build-time environment variables.

```javascript
const apiBase = import.meta.env.VITE_API_BASE_URL;
async function request(path, token, method = "GET", body) {
  const response = await fetch(`${apiBase}/api${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error.message);
  return payload.data;
}
```

Configure `ALLOWED_ORIGINS` as a JSON array of exact frontend origins, including scheme and port. Default origins are `http://localhost:3000` and `http://localhost:5173`. Wildcards are rejected; cookies are not used.

For shared integration, all four developers must use the **same hosted API URL and shared database**. Separate localhost instances have separate data. A future approved shared demo can use one API process and one persistent SQLite volume; PostgreSQL is preferable for multiple workers/hosts. Do not put SQLite on a shared network filesystem. Existing hosted configuration is described in the root README; this guide does not deploy it.

## 4. API contracts

All successful responses use `{"data": ...}`. Create operations return 201; reads and patches return 200. Lists accept `limit` (1–100, default 50) and `offset` (default 0), newest first. Empty lists return `{"data":[]}`. UUIDs are strings and timestamps are UTC ISO 8601. Foreign or nonexistent record IDs both return 404.

| Method | Path | Required body / behavior |
|---|---|---|
| GET | `/api/patients/me` | Current user's profile |
| PATCH | `/api/patients/me` | Optional `display_name`, IANA `timezone`; explicit null rejected |
| GET | `/api/medications` | Current patient's medications |
| POST | `/api/medications` | `name`, `dosage`, `schedule`; optional `active` |
| PATCH | `/api/medications/{id}` | Optional medication fields; set `active:false` to archive |
| POST | `/api/medications/{id}/log` | `status` = `taken` or `skipped`, timezone-aware `recorded_at`; optional `note` |
| GET | `/api/checkins` | Current patient's check-ins |
| POST | `/api/checkins` | `day` = YYYY-MM-DD, `wellbeing` = 1–5; optional `note`; one per patient/day |
| GET | `/api/alerts` | Current patient's stored alerts |
| POST | `/api/alerts` | `category`, `message`; status defaults to `open` |
| POST | `/api/chat/message` | `message`; optional `conversation_id` to continue |
| GET | `/api/chat/conversations` | Current patient's conversation summaries |
| GET | `/api/chat/conversations/{id}` | Conversation and messages |
| GET | `/api/health` | Public migration/database health and integration status |

These routes persist and read real database records. Chat works in `approved_instructions` mode and returns 503 in default `disabled` mode. The deterministic provider quotes approved text; it is not a generative AI implementation. Alerts are stored only: no notifications, escalation, clinical triage, or emergency monitoring. Medication data is user-entered tracking information, not prescribing or dosage recommendations. There are no hard-delete APIs; medication archival uses PATCH.

Example medication request:

```json
{"name":"Fictional demo medication","dosage":"Demo dose","schedule":"Demo schedule"}
```

Example response:

```json
{"data":{"id":"e956de24-c22c-4d79-a1f3-c12a7a018402","created_at":"2026-11-13T17:00:00Z","updated_at":"2026-11-13T17:00:00Z","name":"Fictional demo medication","dosage":"Demo dose","schedule":"Demo schedule","active":true}}
```

Example check-in: `{"day":"2026-11-13","wellbeing":3,"note":"Synthetic check-in"}`. Example alert: `{"category":"demo","message":"Synthetic alert"}`. Example chat: `{"message":"Show my approved instructions"}`. A chat response contains `conversation_id`, `user_message`, and `assistant_message` within `data`. Swagger documents all response fields and constraints.

Errors use `{"error":{"code":"...","message":"..."}}`; validation errors also include sanitized `details` with field locations and types. Codes: 401 invalid/missing demo credentials, 404 missing/not-owned resource, 409 duplicate check-in or constraint conflict, 422 invalid input, 503 unconfigured auth/AI or unavailable database. Provider errors never include prompts, secrets, or provider payloads. Unknown input fields are rejected.

PowerShell sample requests (set the base URL and token in your current shell):

```powershell
$apiBase = 'http://127.0.0.1:8000'
$demoToken = Read-Host 'Enter your generated demo token'
$headers = @{ Authorization = "Bearer $demoToken" }
Invoke-RestMethod "$apiBase/api/patients/me" -Headers $headers
Invoke-RestMethod "$apiBase/api/checkins" -Method Post -Headers $headers -ContentType 'application/json' -Body '{"day":"2026-11-13","wellbeing":3}'
Invoke-RestMethod "$apiBase/api/chat/message" -Method Post -Headers $headers -ContentType 'application/json' -Body '{"message":"Show my approved instructions"}'
```

## 5. Add routes and services

Add a router under `app/api/`, schemas under `app/schemas/`, and business logic under `app/services/`. Register the router once in `app/main.py`. Use `Depends(current_patient)` and `Depends(get_db)` on all patient-data routes. Scope every query to `patient.id`; use `services.records.owned` for ID lookups. Medication logs inherit ownership through their medication. Never trust a patient/user ID from request bodies. Use `Data[YourSchema]` response models. Add cross-user access tests when adding a route.

## 6. Models and migrations

The original core tables cover patients, recovery plans, medications, medication logs, check-ins, conversations, messages, alerts, and care-team connections. Subsequent migrations add medication schedules, risk evaluations, correction/inventory audits, caregiver relationships, and access audits; see the recovery integration guide. Records have UUIDs, created/updated timestamps, foreign keys, and owner indexes. Patients have a unique authenticated identity; check-ins are unique per patient/day; care-team membership is unique per patient/member. Care-team records do not yet grant access to any patient data.

Add models in `app/models/` and import them in its `__init__.py` so Alembic sees them. Then:

```powershell
.\.venv\Scripts\python -m alembic revision --autogenerate -m "Describe schema change"
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m alembic check
```

Review generated migration operations before applying them. Never edit a migration already shared/applied. Coordinate migration ownership; resolve multiple Alembic heads together. Keep health revision checking updated when adding a revision. The initial migration is explicit and independent of future model definitions.

SQLAlchemy uses portable types and relationships. To move to PostgreSQL later, install the psycopg driver, change `DATABASE_URL` to a `postgresql+psycopg://...` connection string, and apply migrations to an empty target. Existing SQLite data needs a separate reviewed export/import. The PostgreSQL compatibility workflow upgrades/checks migrations on a disposable service and tests private-schema ORM access. Most feature tests use SQLite. See the root README for private-schema migration targeting limitations.

## 7. AI and authentication extension points

`app/services/ai.py` defines `AIProvider.respond(prompt, patient_context, history)`. The chat route passes only approved instructions belonging to the authenticated patient, plus the latest 20 messages. Default `AI_PROVIDER=disabled` returns 503 without saving chat messages. `approved_instructions` quotes approved text or clearly reports that none exists. It does not invent advice, diagnose, or follow instructions embedded in prompts.

`AI_API_KEY` is reserved for a future external adapter and is currently unused. Set future credentials only in server environment variables. An adapter must implement request timeouts, bounded outputs, provider error handling, and a reviewed medical-safety policy before enabling generative responses. Register it in `build_provider` and add failure/safety tests. The common service translates provider failures into sanitized 503 responses, and the chat route stores user/assistant messages together only after a valid response.

Local token authentication defaults off and is rejected in production. Hosted shared-code authentication is a separate fictional demo mode. The existing `authenticated_identity` implementation also verifies Supabase bearer tokens against its user endpoint; preserve this server-side verification and `current_patient` ownership mapping. With no provider configured, protected endpoints return 503. Clinician roles, a full production login UI, rate limiting, and comprehensive access auditing remain incomplete; caregiver and correction events already have audit records. See the root README for mode precedence.

## 8. Demo data

`python -m app.seed` creates a synthetic profile and a fictional, nonclinical approved plan for each configured demo identity. It is idempotent and refuses production or disabled demo auth. It never clears existing data. Use the API to add fictional medications, check-ins, and alerts. Clinical approval workflows and recovery-plan/care-team CRUD APIs are future feature work; clients cannot self-approve medical instructions.

## 9. Tests

```powershell
.\.venv\Scripts\python -m pytest -q
```

Tests use migrated temporary SQLite databases and test-only tokens, covering migrations, API startup/docs, CRUD, validation, ownership, CORS, approved content, AI history/failures, and disabled authentication. If Windows denies access to its shared temporary directory, create `.test-tmp` and pass a fresh directory with `--basetemp=.test-tmp/unique-run-name`. Do not point pytest's base temporary directory at a folder containing work; pytest owns that directory.

## 10. Four-developer workflow

Assign feature ownership to independent routers/services; coordinate changes to `auth.py`, model exports, shared schemas, `main.py`, dependencies, and migrations. Use feature branches and small PRs. Agree on schema contracts before frontend integration. Do not commit `.env`, databases, tokens, virtual environments, or real patient data. Avoid logging bodies, authorization headers, database parameters, or clinical content. The documented server command disables access logging; ensure future hosting/proxy logs are similarly configured.

## Environment reference

| Variable | Default | Purpose |
|---|---|---|
| `APP_ENV` | `development` | `development`, `test`, or `production` |
| `DATABASE_URL` | `sqlite:///./urchart.db` | Server-side SQLAlchemy connection URL |
| `ALLOWED_ORIGINS` | localhost ports 3000 and 5173 | JSON array of explicit frontend origins |
| `DEMO_AUTH_ENABLED` | `false` | Opt-in synthetic demo access only |
| `DEMO_TOKENS` | `{}` | JSON mapping secret tokens to stable synthetic identities |
| `AI_PROVIDER` | `disabled` | `disabled` or `approved_instructions` |
| `AI_API_KEY` | empty | Reserved server-side credential; unused until an adapter exists |
