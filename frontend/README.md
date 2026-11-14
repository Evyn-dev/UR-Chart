# UR Chart website (functional demo)

React 19 + TypeScript + Vite + Tailwind 4. Desktop-first patient recovery companion built on the shared Python FastAPI backend. This is an educational hackathon prototype for **fictional synthetic data only**.

## Run locally on Windows

Prerequisites: Node.js 20+ and Python 3.11+.

**Terminal 1, backend**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-lock.txt
Copy-Item .env.example .env
```

Edit ignored `backend/.env` to enable demo authentication, generate your **own** random token, and map it to a synthetic user. Use `python -c "import secrets;print(secrets.token_urlsafe(32))"` to generate a token. An example mapping format is:

```dotenv
DEMO_AUTH_ENABLED=true
DEMO_TOKENS={"REPLACE_WITH_REAL_RANDOM_TOKEN":"synthetic-alex"}
AI_PROVIDER=approved_instructions
```

Do **not** use the placeholder as a token. It must be at least 32 characters and must not be committed. For testing caregiver invitations, add an independently generated second token associated with a *different* synthetic identity.

```powershell
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m app.seed
.\.venv\Scripts\python -m uvicorn app.main:app --reload --no-access-log
```

**Terminal 2, website**, opened from project root:

```powershell
cd frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:5173**. Paste your synthetic token into the demo login. Vite proxies `/api` to the FastAPI server at `http://127.0.0.1:8000`, avoiding local CORS issues. Do not put a token in the source code, URL, or Vite environment variables.

The sign-in screen reads `/api/health` to select the login mode. Local demo tokens are sent unchanged and identify their configured user. The hosted shared-code demo shows a patient/caregiver selector and appends that role only for hosted-code authentication. Deploy the updated API alongside the frontend so it exposes `login_mode`.

## Functional features

- Demo-session entry verified against `/api/patients/me` (token only in browser session storage).
- Overview with medication schedule, active alerts, recovery check-in stats, and links.
- Medication list, add medication, and record **due** doses as taken/skipped/missed.
- Create and correct check-ins; display backend-generated safety guidance.
- View patient-recorded trends and pain chart.
- Safety alerts with acknowledgment, resolution/reopen actions, and explicit emergency guidance.
- Approved-instructions chat with conversation history (only if the backend provider is enabled).
- Caregiver invitations, accept/decline, revoke access, and inspect allowed shared data.
- Demo profile/timezone settings.
- Appointments and care-team messages are deliberately marked **not implemented**.

The frontend relies on Python's rule engine. No independent JavaScript medical classifier is included. Alerts do **not** notify clinicians or dispatchers. Do not use this prototype for medical decisions.

## Checks and troubleshooting

```powershell
cd frontend
npm run build
npm test
npm audit --omit=dev
npm audit
```

If your browser shows "Cannot reach your recovery service", make sure FastAPI is running and `/api/health` loads. If chat returns unavailable, use `AI_PROVIDER=approved_instructions` and seed fictional approved instructions. A real generative AI provider is not part of merged `main` at this point.

The archive was originally created on Windows with `node_modules` included. Reinstall dependencies using `npm ci` on the machine where you will run it. Security audit of the original dependencies was blocked by unavailable registry access in the code-review environment; re-run `npm audit` locally and review all critical findings before deploying.

## Team integration

Work should land through a reviewed frontend branch. Do not overwrite the Python assistant draft PR #5 or the emergency guidance branch. Their routes may be integrated after those changes are merged and tested. The original backend source and migrations were intentionally left untouched.

## One-click local launch (Windows)

From the downloaded project root, double-click **`Launch UR Chart.bat`**. The script creates a Python virtual environment, installs missing backend/frontend dependencies, prepares the SQLite database, and opens the website in your default browser. On first use with no existing `backend/.env`, it generates a **random fictional-demo access token**, stores it in ignored local files, and copies the token to your clipboard so you can paste it into the demo login. Two terminal windows remain open for the Python API and React server. Close them to stop the app.

The launcher does not overwrite an existing `backend/.env`. If one already exists, configure `DEMO_AUTH_ENABLED=true` and synthetic demo identities as described above. It **does not deploy or publish** the app. It requires Python 3.11+ and Node.js 20+, and may need internet access for dependency installation on the first run. Never use real patient data or deploy with demo authentication enabled.
