# UR Chart — Python Recovery Assistant module

This PR replaces the **Java proposal** with Python code that runs inside the team's existing FastAPI service. No Java server is needed. Existing patient, medication, check-in, recovery plan, clinical-risk alert, authentication and conversation modules remain owned by their original contributors.

## Integration points

- Existing `POST /api/chat/message` now passes a **limited, authenticated-patient-only snapshot** of medications, check-ins, and safety alerts to the provider. The approved-instructions provider behaves as before.
- Optional `AI_PROVIDER=openai` uses the existing provider interface and `AI_API_KEY` from the **backend server environment**, with `AI_MODEL` defaulting to `gpt-4.1-mini`. This mode is restricted to development/test with synthetic demo auth. It is **off by default**.
- `POST /api/assistant/triage` recognizes a small set of urgent phrases as a demo safety shortcut before chat. It does **not** replace the team's existing deterministic check-in risk evaluation, and a non-match is **not** an all-clear.
- General-purpose reminders are distinct from clinician/safety alerts. Create/list/action routes use the **same patient identity** and database as the rest of UR Chart.
- One additive Alembic migration (`0006`) creates `personal_reminders`.

## How to run

1. In `backend/`, follow the repository's `BACKEND_GUIDE.md` to configure the team backend and synthetic demo token. Run `python -m alembic upgrade head`.
2. Start the existing FastAPI server with `python -m uvicorn app.main:app --reload --no-access-log` (default port 8000).
3. In another terminal in `frontend/assistant-demo/`, run `python -m http.server 5173`. Open `http://localhost:5173`.
4. Enter the same demo bearer token assigned by the backend; it stays in the page memory and is not included in source or URLs.
5. Use the AI assistant, press Enable Voice, say **“Chart Chart”**, then a question; say **“Chart Emergency”** for the safe emergency demonstration.

For optional generative replies, set `AI_PROVIDER=openai`, `AI_API_KEY=<server-secret>`, and optionally `AI_MODEL` in ignored `backend/.env`, then restart the server. Never commit secrets. Existing `approved_instructions` mode remains available without an external service.

## Routes

| Method | Path | Purpose |
| --- | --- | --- |
| POST | /api/assistant/triage | Limited prototype phrase screening; requires demo auth |
| POST | /api/chat/message | Shared authenticated conversation with optional generative provider |
| GET | /api/reminders | Patient's custom reminders |
| POST | /api/reminders | Create `title`, `notes`, timezone-aware `due_at`, IANA `timezone`, `repeat` |
| POST | /api/reminders/{id}/action | `complete`, `snooze` (10m), `toggle`, `delete` |

Repeats: `once`, `daily`, `weekdays`, `weekly`, `monthly`. Dates are stored in UTC; recurrence is computed in the user's selected IANA timezone.

## Safety, privacy, and limits

**This is for synthetic-data demonstration, not clinical care.** Browser speech recognition only works on supported browsers while the page is allowed to listen. Browser reminder notifications only work with the page and API running; no background push service is present. “Chart Emergency” opens an emergency screen; it **does not** auto-dial 911 or send location to responders. Geolocation requires explicit permission and must be conveyed to dispatch manually. The limited phrase matcher is not medically validated, and cannot detect all emergencies. The existing shared safety engine remains separate.

External AI is intentionally forbidden in production and when demo authentication is disabled. An actual patient product needs consent, privacy/security reviews, clinical validation, and a compliant service arrangement before real personal health information is sent to any model provider. Do not include private patient records or credentials in GitHub, screenshots, or demo logs.

## Tests

From `backend/`: `python -m pytest -q`. Tests cover reminder ownership, recurrence, validation, auth, triage, and unchanged chat and health endpoints. Teammates should review migration ordering and PR integration before merging.
