# UR Chart (Urgent Recovery)

A desktop-first recovery companion website for the NC A&T Medtronic Hackathon. Educational prototype for **fictional demonstration data only**, not a medical device or clinical triage service.

## Open the app on Windows

After downloading or cloning this repository, **double-click [`Launch UR Chart.bat`](Launch%20UR%20Chart.bat)** in the project root.

The shortcut invokes `scripts/launch-ur-chart.ps1`. It requires Python 3.11+ and Node.js 20+, installs missing local dependencies, sets up an SQLite database and fictional demo credentials on a fresh installation, starts the Python FastAPI server and React website in separate terminals, and opens http://127.0.0.1:5173 in your browser. Keep both server terminals open while testing. An existing `backend/.env` is never overwritten.

On a fresh setup, the launcher copies the generated fictional demo token to your clipboard for pasting into the login screen. The token and local database are ignored by Git. Do not use real patient data.

For manual setup and troubleshooting, see [frontend/README.md](frontend/README.md) and [backend/README.md](backend/README.md). The backend API documentation is available at http://127.0.0.1:8000/docs.

## Current capabilities

The React frontend connects to the Python/FastAPI medication, check-in, recovery trends, safety alerts, chat, and caregiver APIs. Some team features remain in unmerged branches and are not automatically activated by this website. Care-team messaging and appointments do not yet have working backend integrations.

**Warning:** Demo bearer tokens, prototype risk rules, and fictional discharge instructions are not production-grade security or clinical decision support. Do not expose this app to real patients.
