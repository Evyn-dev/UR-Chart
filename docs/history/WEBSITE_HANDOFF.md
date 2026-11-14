> Historical snapshot, not current setup or verification. See [current README](../../README.md) and [cleanup report](../REPOSITORY_CLEANUP.md).

# UR Chart website handoff (2026-11-14)

## Current implementation

This website extends the existing `frontend/` foundation from the supplied ZIP. It did **not** replace the shared HTTP client, typed services, backend, migrations, or other teammates' modules.

New: `src/main.tsx`, `src/App.tsx`, `src/styles.css`, reusable `src/components/{Shell,UI}.tsx`, and `src/pages/Pages.tsx` (dashboard, medications, check-in, progress, alerts, assistant, caregivers, settings). Added `src/services/patients.ts`, two frontend unit test files, frontend README, and test setup.

Features are deliberately bound to the existing FastAPI `/api` endpoints. Vite uses a same-origin proxy during development. A real bearer token is requested at runtime and stored in session storage only. This is a fictional-data development prototype, not production authentication.

## Verification performed in this environment

- `tsc -b` from `frontend/`: **passes**.
- `python -m pytest -q` from `backend/`: **76 passed**.
- A full Vite build and Vitest run were **not possible** here. The uploaded `node_modules` were installed for Windows; this Linux execution environment lacks the Rollup native Linux binary. A clean `npm ci` could not finish because package-registry access timed out. Run `npm ci`, `npm run build`, `npm test`, and `npm audit` on your Windows development machine.

## Known limitations / review priorities

1. **Dependency vulnerabilities** from the original npm install (1 moderate, 2 critical in the prior handoff) have not been verified or remediated. Run a full npm audit locally, review production vs dev dependency findings, and fix before any public deployment.
2. Frontend page components are intentionally bundled in `src/pages/Pages.tsx` for an initial functional pass. Codex can split and polish them after end-to-end verification.
3. Medication scheduling, risk evaluation, dose/inventory rules, and caregiver access permissions are owned by **FastAPI**. The frontend never uses an independent classifier.
4. `feature/python-ai-recovery-assistant` PR #5 remains **draft**. This website currently targets the merged `/api/chat/*` endpoints only. Integrate new assistant/reminder endpoints after PR #5 is reviewed and merged, and migrations are checked.
5. `feature/emergency-guidance` is unmerged, and has duplicate keyword triage code. Do not merge it as a second authoritative risk engine. The older Java assistant PR #4 is superseded by #5.
6. Appointments and care-team messages are explicit unavailable pages; no API contract exists for them on merged main.
7. Alert resolution is an *audit action*, not a clinical declaration that symptoms are safe. Emergency guidance and direct call instructions remain visible.
8. No production auth, hosted notifications, real clinical approval, or automated emergency communications exist. **Synthetic data only**.
9. For smooth UI review, verify at 1440px desktop, 768px tablet, and 375px phone. The design is desktop-first but has responsive layout rules.
10. Inspect same-day check-in corrections and caregiver identity switching in a browser; the API and type checks pass, but full frontend E2E automation has not been run.

## Git branch state

ZIP's original HEAD is `ce2d30b` on `main`, matching the upstream base at the time of inspection. The new local branch `feature/website-frontend` contains only website code. Because direct network access to github.com was unavailable from this execution container, **nothing was pushed or merged**. Leave existing teammates' feature branches and draft PRs untouched. Review the website as a branch before merging it into `main`.

## To test on Windows

Follow `frontend/README.md`: configure `backend/.env` with random demo token(s), run Alembic migrations and synthetic seed, launch FastAPI on port 8000, then from `frontend/` run `npm ci` and `npm run dev`. Sign in on `http://127.0.0.1:5173` using one of the generated fictional patient tokens.

## Windows shortcut

A root-level **`Launch UR Chart.bat`** launches `scripts/launch-ur-chart.ps1` to set up dependencies (if missing), create local synthetic demo credentials on a fresh install, run database migrations and seed data, open FastAPI + Vite in separate windows, and launch the browser. It never overwrites an existing `.env` file. The synthetic token is generated randomly, saved in ignored `backend/.demo-access-token`, and copied to the clipboard for demo login. See `frontend/README.md` for requirements and limitations.
