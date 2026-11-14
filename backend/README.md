# UR Chart backend

FastAPI + SQLAlchemy + Alembic; SQLite by default. See [BACKEND_GUIDE.md](../BACKEND_GUIDE.md) for setup, API contracts, frontend integration, authentication, AI extension points, and team workflow.

Run commands from this directory. Python 3.11+ is required; verified with Python 3.14 on Windows.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-lock.txt
Copy-Item .env.example .env
# Configure demo authentication in .env as described in the guide.
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m app.seed
.\.venv\Scripts\python -m uvicorn app.main:app --reload --no-access-log
```

API docs: http://127.0.0.1:8000/docs

## Presentation data readiness (fictional demo only)

After deploying the latest backend code and applying Alembic migrations, run these commands
**on the computer/server connected to the same database as the Cloudflare demo**:

```powershell
cd backend
python -m alembic upgrade head
python -m app.presentation_demo --seed
python -m app.presentation_demo --check
```

Use the `backend/.venv/Scripts/python.exe` interpreter if your setup uses the launcher virtual environment.
The command is intentionally limited to `synthetic-demo-patient` and requires a matching
configured demo login (local `DEMO_TOKENS` or hosted `HOSTED_DEMO_CODE_HASH`).
`--seed` fills missing fictional records without overwriting user-entered check-ins,
and `--check` performs **read-only** checks and returns a nonzero exit code on missing
data. It does not restart servers, change Cloudflare configuration, or insert real records.

For the presentation, sign in with the **same demo access code** and choose **Caregiver**.
The demo caregiver should see Jordan Ellis's 7-day recovery trends, medication adherence,
selected alert, and editable educational curriculum. Patients can ask Clara about their
recorded checklist; generated responses require the configured AI provider to be available.
The database check is not a substitute for opening the live page in a browser.


## Shared Documents (fictional demo only)

The **Documents** navigation item is available in both patient and caregiver views.
Patients can upload PDF, DOCX, PNG, JPEG, and UTF-8 text files (up to 3 MB),
download them, delete them, and explicitly share or unshare each file with
currently accepted caregivers. Files start private. A caregiver can view
patient-shared files, upload a document to an accepted patient's record,
and download their own contributed documents while the relationship is active.
Revoking an invitation immediately removes caregiver document access.

Storage is in the same backend SQL database (binary column), not on the browser
or in GitHub. The documents table is created automatically by the app only
in development/test mode; when using an isolated *hosted fictional demo* DB,
run `python -m app.init_documents` once on the backend before starting the server.
If the database is recreated, uploaded documents will be lost.

Do not use this prototype for real patient information: production requires
reviewed migrations, secure object storage and encryption policies, malware
scanning, retention/deletion policies, HIPAA/privacy review as applicable,
and dedicated user accounts instead of shared demo credentials.
