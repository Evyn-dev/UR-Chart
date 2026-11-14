# Deploying UR Chart to Vercel

## Configuration reference

The repository's hosted smoke workflow targets `https://ur-chart-api.vercel.app`; the frontend project uses `https://ur-chart.vercel.app`. Treat these as configured targets, not proof of live availability. Check the latest deployment and smoke results before a demo.

The frontend uses root `frontend`, `npm ci`, `npm run build`, and output `dist`. The backend entry point is `backend/index.py`. Existing project settings and secrets are managed outside Git and must be preserved. This cleanup does not redeploy either project.

This guide prepares the **React + TypeScript frontend** for Vercel hosting. Vercel does **not** automatically host the project's existing Python FastAPI server or persistent SQLite database when importing the `frontend/` directory.

UR Chart is an educational hackathon prototype. Use synthetic patient data only. The current demo-token authentication and risk classification are **not approved for real patients or public clinical use**.

## 1. Import the existing GitHub repository

1. In the [Vercel Dashboard](https://vercel.com/new), select **Add New Project** and import the private repository `Evyn-dev/UR-Chart`. Authorize Vercel's GitHub integration for this repository if prompted.
2. Set **Root Directory** to **`frontend`**. Do not choose the repository root.
3. Select the **Vite** framework preset (the repository already includes `frontend/vercel.json`).
4. Use install command **`npm ci`**, build command **`npm run build`**, and output directory **`dist`**.
5. Deploy from the `main` branch. After the Git integration is set up, subsequent pushes to `main` should trigger frontend deployments automatically.

The Vercel configuration includes a single-page-app fallback so deep links like `/medications`, `/check-in`, and `/assistant` can be refreshed directly.

**What works before the backend is hosted:** the React site loads, but login and patient data API calls will fail. This is expected, because the browser cannot reach a Python server running on a developer's localhost.

## 2. Host the Python API separately

Keep FastAPI in Python and deploy it using a persistent service and database (for example, a Python service host with an external PostgreSQL database). **Do not simply upload the existing SQLite file to a serverless function**: writes will not be reliably persistent across instances.

Before allowing remote users to test:

- Use separate synthetic/test identities and limit who can reach the prototype.
- Set a trusted, exact `ALLOWED_ORIGINS` value for the deployed HTTPS Vercel website, instead of relying on localhost defaults.
- Configure the backend database and run Alembic migrations on the hosted database.
- Replace development-only demo token authentication with appropriate real authentication before using any actual health data.
- Do not run prototype medical risk rules as a real clinical assessment. No emergency calls or notifications are automatically sent.
- Never commit backend `.env`, database credentials, service tokens, or real records.

## 3. Connect the frontend to the hosted API

Once there is a trusted HTTPS Python API origin, open the Vercel project:

**Settings → Environment Variables**, add:

```text
VITE_API_BASE_URL=https://your-python-api.example
```

Use the API **origin only**, not a URL ending in `/api`. For example, the frontend requests `https://your-python-api.example/api/patients/me`.

This `VITE_*` variable is intentionally public in the browser bundle. **Never place a private token, secret, or database password in it.** Redeploy after changing a Vite build-time variable.

## 4. Test deployment

- Confirm a clean Vercel build from `npm ci` and `npm run build`.
- Verify the homepage and page-refresh routing for `/medications`, `/check-in`, and `/assistant`.
- Verify the deployed FastAPI `/api/health` endpoint over HTTPS.
- Verify that the allowed-origin and authentication configuration is correct for the frontend.
- Use synthetic accounts to test medications, check-ins, caregiver revocation, and alerts.
- Run `npm audit` and address critical production/development findings before opening the site broadly.

## Local development

The one-click Windows launcher and local Vite proxy continue to use `http://127.0.0.1:8000`. They do not affect Vercel hosting. Leave `VITE_API_BASE_URL` unset for the usual local proxy workflow.

See [the root README](../README.md) for local setup and authentication.
