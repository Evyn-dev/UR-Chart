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

## Zero-credit AI setup for demo day (Windows)

**No OpenAI API balance is needed.** The shared FastAPI app can use a local Ollama model.

1. Install Ollama for Windows from https://ollama.com/download and open the Ollama app.
2. In any PowerShell terminal run `ollama pull llama3.2:3b` (requires an internet connection once to download model weights). If the CLI is not recognized, reopen the terminal after installation.
3. Edit **ignored** `backend/.env`: set `AI_PROVIDER=ollama` and `LOCAL_AI_MODEL=llama3.2:3b`. Remove the exposed/revoked OpenAI API key or leave `AI_API_KEY=` empty.
4. With your existing demo token and virtual environment active, restart backend from `backend/`: `python -m uvicorn app.main:app --reload --no-access-log`.
5. Keep `frontend/assistant-demo` served on port 5173 and connect with the *demo bearer token*, not an API key. Ask a recovery question. Local model calls can be slower on first load.
6. If Ollama cannot be installed today, use `AI_PROVIDER=approved_instructions` instead: this is a reliable, offline, **non-generative** demo mode that quotes only the approved instructions, while voice and reminders continue to work.

Optional verification: `ollama list` should display `llama3.2:3b`; `ollama run llama3.2:3b "Say hello"` checks whether the model can generate. The Ollama service must be available on `http://127.0.0.1:11434`, its default localhost address. No Python `openai` package is required by our production code (the paid adapter uses `httpx`).

Local AI is still **not clinically validated**, is not automatic 24/7 monitoring, and is for fictional data only. A localhost model reduces the need to send demo conversation text to a third-party model API but is not proof of production-grade privacy or compliance. Browser microphone and browser notifications remain active-tab demonstrations, not background phone features.

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
