# Assistant and personal reminders integration

This branch selectively adapts the local provider and React voice features from PR #8 and the reminder model/API/service from PR #7 onto the modular frontend from merged PR #9. It does not merge either source branch wholesale. Existing chat routes, history, authentication, medication scheduling, and risk evaluation remain authoritative.

## Assistant

Hosted deployments should retain `AI_PROVIDER=approved_instructions`. For optional local generation, run Ollama on the backend machine, install a model, and set these values in ignored `backend/.env`:

```dotenv
APP_ENV=development
AI_PROVIDER=ollama
LOCAL_AI_MODEL=llama3.2:3b
LOCAL_AI_TIMEOUT=20
```

The adapter calls only `http://127.0.0.1:11434/api/chat`, with proxy environment variables and redirects disabled. It uses approved plans, active medications, recent check-ins/alerts, and conversation history belonging to the authenticated patient. No hosted AI account or API key is required. Production, test, and Vercel environments select approved instructions even when configured for Ollama. Local connection, timeout, malformed, empty, or oversized response failures fall back to approved instructions. Response text distinguishes generated drafts, fallback, and deterministic quotes. Local generation is not clinically validated.

Voice and spoken replies are separate opt-ins. Recognition requires browser support and microphone permission; the browser may use its own recognition service. “Chart Chart” precedes a question; “Chart Emergency” only opens static guidance. Leaving the page stops recognition. There are no automatic calls or new medical classifiers.

## Reminders

The dedicated React Reminders page uses the existing session/client/UI components. `GET /api/reminders` supports offset/limit and optional active filtering; `POST` creates a reminder, `PATCH /{id}` replaces editable fields, and `POST /{id}/action` accepts complete, dismiss, snooze, toggle, or delete. Updates/actions require `expected_version`; concurrent changes return 409 rather than overwriting a newer version. Every query/action is patient-scoped. Reminder contents are not shared with caregivers.

Schedules support once, daily, weekdays, weekly, and monthly. The explicit first due instant is retained; recurrence uses its original local wall time in the selected IANA zone. Completion/dismissal deactivates one-time reminders or schedules the next future recurring occurrence, skipping overdue occurrences. Monthly schedules clamp short months and restore the original day in later months. Fall overlaps use the first occurrence; spring gaps shift that recurring occurrence forward by the gap without moving the anchor. The creation form rejects a nonexistent initial wall time. Snooze moves a currently due reminder ten minutes forward without shifting its recurrence anchor. Editing resets the anchor; it does not reactivate inactive reminders.

Browser notifications require explicit permission and an open app session. Polling runs across authenticated routes every 30 seconds, with generic notification text and per-session deduplication. Refresh requires enabling notifications again. Sleeping devices, background throttling, unsupported browsers, and denied permission can prevent or delay delivery. There is no closed-site delivery, worker, cron, SMS, email, or medication alarm service.

## Database and rollout

Migration `0006` follows `0005` and adds only `personal_reminders`. Migrations `0001`–`0005` are unchanged. It includes ownership, recurrence anchor, version and last-action fields. Downgrade refuses to drop a populated reminder table.

For a configured PostgreSQL `DATABASE_SCHEMA`, Alembic now requires that schema to exist, targets its own version table, and uses a transaction-local search path with no public fallback. It does not provision schemas or change grants. Missing schemas fail explicitly. Private-schema offline SQL generation is unsupported; use an online connection. Runtime ORM translation remains unchanged.

After review and before deploying the integration backend, take the normal database backup and run `python -m alembic upgrade head` followed by `python -m alembic check` with the intended database URL/schema and migration role. Coordinate the release: the existing health check requires the database revision to match the deployed code. No hosted patient database was modified during this integration.

## Verification

- Local full backend suite: 127 passed, 2 PostgreSQL-only tests skipped. SQLite fresh/populated upgrade coverage, ownership, existing caregiver/security regressions, fallback, recurrence/DST, and version conflicts pass.
- Frontend: 24 tests, TypeScript and production build pass; npm audit reports zero vulnerabilities.
- Browser against an isolated synthetic SQLite database: create, refresh, edit and complete reminder; send chat, refresh and reopen history; emergency guidance display all passed.
- PostgreSQL CI includes fresh public-schema migration/check and a populated `0005` → `0006` private-schema migration, API ownership/version checks, unchanged public revision, and refusal of a populated downgrade. Consult the integration PR checks for its final result.
- Actual Ollama model inference, physical microphone/speaker behavior, and real OS notification delivery were not exercised. Provider and browser permission/compatibility paths have automated tests.

Primary changes: `backend/app/services/{local_recovery,chat_context,reminders}.py`, reminder API/model/schema and migration/environment; `frontend/src/pages/{AssistantPage,RemindersPage}.tsx`, `components/ChartVoice.tsx`, notification hook, reminder service, routing/navigation; corresponding backend/frontend tests. No additional runtime dependencies or production deployments are introduced.
