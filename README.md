# UR Chart (Urgent Recovery)

A recovery companion for the NC A&T Medtronic Hackathon. **Fictional demonstration data only.** This prototype is not clinically validated and is not an emergency monitoring service.

## What works

Medication schedules and dose records, inventory/refill indicators, audited corrections, daily check-ins, descriptive trends, prototype safety alerts, consent-based caregiver summaries, and stored chat conversations. Chat can quote approved instructions when enabled. Voice, generative AI, and personal reminders remain unmerged work; appointments and care-team messaging are explicitly unavailable.

## Architecture

| Responsibility | Authoritative implementation |
| --- | --- |
| Website and routing | `frontend/src/App.tsx`, individual `pages/` modules |
| Session and HTTP boundary | `hooks/session.tsx`, `services/client.ts`, typed feature services |
| API routes and JSON schemas | `backend/app/api/`, `backend/app/schemas/` |
| Verified identity and ownership | `backend/app/auth.py`, `services/records.py`, caregiver service |
| Recovery business logic | `backend/app/services/{medications,checkins,corrections,summaries}.py` |
| Safety evaluation and audit | `services/risk.py`, server-controlled rules, alert records |
| Chat/provider boundary | `api/chat.py`, `services/ai.py` |
| Database and migrations | `app/database.py`, SQLAlchemy models, `migrations/versions/` |

React 19 + TypeScript + Vite communicates with FastAPI through `/api`. Successes use `{"data": ...}`; errors use `{"error": ...}`. FastAPI owns authorization and medical screening. SQLAlchemy uses SQLite locally or PostgreSQL when configured. All five existing migrations are retained unchanged.

## Local setup

Use Python 3.11+ and Node.js 22 (matching frontend CI). On Windows, double-click [Launch UR Chart.bat](Launch%20UR%20Chart.bat). The launcher installs missing dependencies, creates a local SQLite demo on first use, copies a generated token to the clipboard, and starts both servers. It preserves an existing `backend/.env`.

For manual setup, from the repository root:

```powershell
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-lock.txt
Copy-Item .env.example .env
```

Copy the example only on a fresh setup. In ignored `backend/.env`, enable `DEMO_AUTH_ENABLED=true`, set `DEMO_TOKENS` to a JSON object mapping independently generated secret tokens to synthetic identity names, and optionally set `AI_PROVIDER=approved_instructions`. Generate each token locally with `python -c "import secrets; print(secrets.token_urlsafe(32))"`. Tokens must be at least 32 characters. Never commit generated tokens.

Then, from `backend/`:

```powershell
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m app.seed
.venv/Scripts/python -m uvicorn app.main:app --reload --no-access-log
```

In a second terminal, from the repository root:

```powershell
cd frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173 and enter your token. Vite proxies `/api` to http://127.0.0.1:8000. Swagger is at http://127.0.0.1:8000/docs. On macOS/Linux use `.venv/bin/python` and `cp` instead of the Windows equivalents.

## Configuration and authentication

Backend settings load from `backend/.env` when started in that directory. Use [backend/.env.example](backend/.env.example) as a starting point. Existing hosting configuration must be retained.

| Setting | Meaning |
| --- | --- |
| `APP_ENV` | `development`, `test`, or `production`; production rejects local demo tokens and prototype risk evaluation |
| `DATABASE_URL` | Local SQLite by default; PostgreSQL uses `postgresql+psycopg` and requires the psycopg driver |
| `DATABASE_SCHEMA` | Optional existing private PostgreSQL schema for runtime ORM routing; not a schema-provisioning command |
| `ALLOWED_ORIGINS` | JSON list of exact permitted frontend origins; no wildcard |
| `DEMO_AUTH_ENABLED`, `DEMO_TOKENS` | Local fictional identity mapping; first authentication mode when enabled |
| `HOSTED_DEMO_CODE_HASH` | SHA-256 hex hash of a separately managed shared demo code; enables fictional patient/caregiver personas |
| `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` | Paired settings for server-side verification of an existing Supabase bearer token when demo modes are off |
| `AI_PROVIDER` | `disabled` or `approved_instructions`; no generative provider on main |
| `AI_API_KEY` | Reserved setting; currently unused by merged providers |
| `RISK_RULES_FILE` | Optional server-controlled rule JSON; default rules are prototype-only |
| `VITE_API_BASE_URL` | Frontend build-time API origin, without `/api`; unset for local Vite proxy |

Login discovers the mode from `/api/health`. Local tokens are submitted unchanged. Hosted demo mode sends the shared code with the selected patient/caregiver persona. The code is not a production identity system. Supabase tokens are verified server-side; there is no email/password login UI in this frontend. The browser keeps the credential in session storage, never in a URL. Do not put secrets in `VITE_*` variables.

Caregiver access requires an invitation to a configured demo identity, acceptance, and explicit sharing permissions. The server enforces permission changes and revocation. A caregiver never receives patient chat or unrestricted account access. For local testing, configure a separate identity and token for the caregiver.

## Database migrations

Run `python -m alembic upgrade head` and `python -m alembic check` from `backend/` using its virtual environment and intended database configuration. Never reset a shared database or edit applied migration files. Add a migration for future schema changes.

For PostgreSQL install `python -m pip install "psycopg[binary]>=3.2,<4"` in the virtual environment. The locked local dependency set does not include this optional driver. Runtime `DATABASE_SCHEMA` translation and migration targeting are different: the current Alembic environment does not provision/target a private schema from that setting. Preserve the established hosted schema workflow; do not run migrations against a private-schema deployment without checking the target with its owner.

## Testing

From `backend/`: `python -m pytest -q` using the virtual environment. Fixtures migrate fresh temporary SQLite databases. The PostgreSQL workflow separately upgrades/checks a disposable PostgreSQL service and tests private-schema ORM access; most feature tests still use SQLite fixtures. Never aim the PostgreSQL test at patient data.

From `frontend/`: `npm ci`, `npm test`, `npm run build`, and `npm audit`. Build includes TypeScript validation. CI also audits production dependencies. See [cleanup verification](docs/REPOSITORY_CLEANUP.md#verification) for actual results and limits.

## Hosting and team integration

Preserve existing Vercel/Supabase project settings and environment secrets. Frontend Vercel configuration lives in `frontend/vercel.json`; the Python entry point is `backend/index.py`. A hosted API needs durable PostgreSQL storage, not a serverless SQLite file. See [frontend deployment](frontend/DEPLOY_VERCEL.md). The hosted smoke workflow checks API health, rejected authentication, and CORS; it is not proof that all patient workflows work online.

Teammates should use a common reachable API origin with separate authorized identities. Separate localhost databases do not share records. Keep API contracts compatible and route backend changes through reviewed migrations. See [backend integration](BACKEND_GUIDE.md), [recovery/caregiver contracts](backend/RECOVERY_TRACKING.md), and [branch inventory](docs/REPOSITORY_CLEANUP.md).

## Known limitations

- Safety rules and keyword screening are prototype-only; alerts are not diagnoses or clinical clearance. For a possible emergency, contact emergency services (911 in the United States).
- Alerts are stored and may be visible to authorized caregivers. No SMS, push, email, automatic emergency call, or clinician notification delivery is implemented.
- Missing dose records are not proof of missed medication; trends are descriptive, not predictions.
- Caregiver invitations currently accept configured demo identities, not arbitrary production users.
- Some frontend lists show only the first API page. Backend pagination is available; full pagination UI remains follow-up work.
- PRs #7/#8 contain unique assistant/reminder work requiring reconciliation. They are not activated by this cleanup.
- Historical implementation notes are retained under [docs/history](docs/history/WEBSITE_HANDOFF.md), not current operating instructions.
