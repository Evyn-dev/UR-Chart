# UR Chart (Urgent Recovery)

A desktop-first recovery companion website for the NC A&T Medtronic Hackathon. Educational prototype for **fictional demonstration data only**, not a medical device or clinical triage service.

## Open the app on Windows

After downloading or cloning this repository, **double-click [`Launch UR Chart.bat`](Launch%20UR%20Chart.bat)** in the project root.

The shortcut invokes `scripts/launch-ur-chart.ps1`. It requires Python 3.11+ and Node.js 20+, installs missing local dependencies, sets up an SQLite database and fictional demo credentials on a fresh installation, starts the Python FastAPI server and React website in separate terminals, and opens http://127.0.0.1:5173 in your browser. Keep both server terminals open while testing. An existing `backend/.env` is never overwritten.

On launch, an explicitly isolated fictional presentation mode provides **Enter as Patient** and **Enter as Caregiver** buttons with no emails or codes. The script generates a fallback local token on first install but does not display it. This one-click mode runs only in development/test, never production or Supabase authentication. The synthetic demo database is prepared on launch; real medical data must not be entered.

For manual setup and troubleshooting, see [frontend/README.md](frontend/README.md) and [backend/README.md](backend/README.md). The backend API documentation is available at http://127.0.0.1:8000/docs.

## One-click presentation mode\n\nDouble-click **Launch UR Chart.bat**, then choose **Enter as Patient** or **Enter as Caregiver** on the landing page. This sets `PRESENTATION_DEMO_ENABLED=true` only in the launcher processes (no edits to your existing `.env`). The fictional patient Jordan Ellis has seven days of check-ins, three demo medications, and a preaccepted fictional caregiver relationship. The restored pre-curriculum app is preserved; previously rolled-back curriculum/graph features are not reintroduced.\n\nIf you start FastAPI without the launcher, set `PRESENTATION_DEMO_ENABLED=true` in its environment **only for a disposable development/test demo** and run `python -m app.seed` after migrations. Code-free access is intentionally public to anyone reaching the tunnel, so use strictly fictional data and stop the tunnel after the presentation. A Cloudflare Quick Tunnel forwards to the local Vite server but is not started by this launcher.\n\n## Current capabilities

The React frontend connects to the Python/FastAPI medication, check-in, recovery trends, safety alerts, chat, and caregiver APIs. Some team features remain in unmerged branches and are not automatically activated by this website. Care-team messaging and appointments do not yet have working backend integrations.

**Warning:** Demo bearer tokens, prototype risk rules, and fictional discharge instructions are not production-grade security or clinical decision support. Do not expose this app to real patients.
