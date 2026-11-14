# Vercel multi-service deployment proposal

This branch is a **proposal awaiting confirmation**, not a verified production deployment. Import `Evyn-dev/UR-Chart` into Vercel with the **repository root (`./`)** as the project Root Directory, and use the **Services** framework/configuration, not Next.js and not the `frontend` subdirectory.

## Services and routing

- `backend`: FastAPI from `backend/`; `backend/index.py` exposes `app` from `app.main`. The existing FastAPI routers already use the `/api` prefix. The public rewrite `/api/(.*)` passes the original path through; do **not** remove the `/api` prefix.
- `frontend`: React/TypeScript/Vite from `frontend/`, built with `npm run build` into `dist/`. All remaining public routes go to the frontend. Its service-scoped SPA rewrite targets `/index.html` for client-side routes (e.g. `/medications`).
- Public top-level routing: `/api/*` → backend, then catch-all `/*` → frontend.

## Service bindings

**None.** The frontend is a static Vite browser app. `frontend/src/services/client.ts` makes browser-origin `fetch('/api/...')` requests which Vercel's public rewrite routes to FastAPI. Service bindings inject runtime variables into *server-side callers*, not into static HTML or browser bundles. There are no backend-to-frontend calls or other inter-service server-side HTTP calls to bind. Do not add an unused `BACKEND_URL` binding to a static frontend or a `VITE_*` environment variable containing an internal URL.

Local development continues to use `frontend/vite.config.ts` proxying `/api` to local FastAPI at `127.0.0.1:8000`; `vercel dev` is the integrated test route once the Vercel project is linked.

## Existing configuration and deployment safeguards

- The root `vercel.json` is authoritative **when the Vercel project uses `./` as Root Directory**. Nested `frontend/vercel.json` and `backend/vercel.json` are legacy, standalone deployment configurations and must not be used to import the combined project.
- Root Git deployments are disabled pending review; do not turn them on until Vercel accepts Services mode and the linked repository and runtime setup are verified.
- Production FastAPI requires `APP_ENV=production`, persistent PostgreSQL storage (`DATABASE_URL`; optional `DATABASE_SCHEMA`), `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, server-only `SUPABASE_SERVICE_ROLE_KEY`, and shared `REDIS_URL`. The database must have Alembic migrations applied. Never use a serverless SQLite file or commit secrets.
- The Vite frontend does not need `VITE_API_BASE_URL` in same-origin Services mode; remove any old value from this new project. Supabase service role keys, Redis credentials, and database credentials must be server-only.
- `/api/health` checks database readiness/migrations. A green static frontend build alone does not establish that the backend is ready.
- This is a fictional-data-only prototype, not validated for real patient use.

## Checks after confirmation

1. Review service names, exposed paths, and the absence of inter-service bindings.
2. Verify Vercel Git integration can access **Evyn-dev/UR-Chart** (not **JerGus-coding/ur-chart**).
3. Create a Vercel Services project using repo Root Directory `./`, connect required backend environment variables and persistent services, run Alembic migrations against the intended database, and deploy a protected preview.
4. Check `/api/health`, browser API calls, and refresh of deep-linked SPA routes; run frontend build/tests and backend tests.
5. Keep patient information out of testing; do not enable public production traffic until safeguards and requirements are validated.
