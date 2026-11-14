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
