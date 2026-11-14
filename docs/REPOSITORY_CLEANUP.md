# Repository cleanup audit

Baseline: `origin/main` at `4ed31e1`, inspected November 14, 2026. Cleanup branch: `refactor/repository-cleanup`. No remote branches deleted, PRs closed, shared history rewritten, or database/deployment settings modified.

## Branch inventory

Counts below are commits unique to main / unique to branch at the audited baseline. Counts do not establish semantic equivalence: overlapping patches were also inspected.

| Branch | Main / branch | Assessment and recommendation |
| --- | --- | --- |
| `main` | 0 / 0 | Authoritative integrated React/FastAPI app, auth fixes, screening, hosted smoke and PostgreSQL checks. |
| `feature/ai-in-team-react-app` (`b1992c0`, PR #8) | 6 / 7 | Open draft; conflicting with main at inspection. Preferred future React assistant path: adds ChartVoice, local provider, patient-scoped context. Not integrated. Rebase/reconcile into the extracted AssistantPage, preserving current auth, chat ownership and provider error behavior. |
| `feature/offline-python-recovery-assistant` (`28f3597`, PR #7) | 42 / 7 | Open draft; conflicting with main. Unique patient-owned reminders, migration 0006, reminder schemas/services/tests, provider adapters and standalone demo. Preserve reminders and provider tests for selective future integration. Do not install a second standalone UI alongside the React app. |
| `feature/python-ai-recovery-assistant` (`126f261`) | 42 / 1 | Commit is an ancestor of the offline branch. Superseded as an integration source by PR #7; archive candidate only after owner confirms and PR #7 work is preserved. |
| `feature/api-reliability` (`9de232d`) | 42 / 7 | Partially superseded in behavior: main now has stale-evaluation refresh, screening fixes and historical alert handling. Still has unique app-factory/lifecycle refactoring. Do not merge its old factory over main's private-schema setup. Review remaining lifecycle improvements separately. |
| `feature/emergency-guidance` (`9d5fd87`) | 43 / 8 | Overlaps main's prototype screening but contains unique Python emergency module plus standalone JavaScript classifier. Preserve branch for rule review; main's Python risk service remains authoritative. No evidence to safely declare the whole branch obsolete. |
| local `feature/website-frontend` (`ce2d30b`) | local only | Original checkout has untracked paused scaffold. Left untouched. Do not discard without reviewing its owner’s work. |

No remote feature branch is fully merged by ancestry. The GitHub REST open-PR listing independently confirmed #7 and #8 are the only open PRs at inspection. (The connector's issue search returned an incomplete empty result.) No closure is proposed by this cleanup.

### Assistant integration decision

PR #8 matches the existing React chat and is the preferred UI starting point. Main still has only disabled/approved-instructions providers. The retained `Pages.tsx` exports preserve existing import consumers, but PR #8's component edits should move to `AssistantPage.tsx`. Keep provider selection in `services/ai.py`; reconcile the overlapping local provider implementations rather than adding both.

PR #7's `/reminders` routes, `PersonalReminder` model, reminder service/schemas, `0006_personal_reminders.py`, and tests remain on its branch unchanged. They are useful, unmerged functionality, not dead code. Before integration, verify migration ancestry, ownership, action semantics, and tests against latest main. No reminder notification delivery should be inferred from stored reminders.

## Duplicate code and ownership report

- Split the multi-page `Pages.tsx` into nine focused route modules. Existing named exports remain as a compatibility barrel. App imports are direct.
- Extracted shared dose controls into `DaySummary`, shared grid/notice/lazy-chart rendering into `RecoveryUI`, and patient-local date-window logic into `useWindow`. These retain their existing behavior without introducing a second implementation.
- Consolidated the duplicated severity-sort expressions in dashboard and alert history into `orderAlerts`. It copies inputs and preserves all records; callers explicitly select which records they display. A regression test verifies emergency ordering and retained resolved history.
- Removed unused imports exposed by the split. No new dependency, visual redesign, or API contract was introduced.
- Backend auth/ownership (`auth.py`, `records.py`), database session factory (`database.py`), medication/check-in/correction services, risk engine, caregiver scopes, and chat/provider boundary are already centralized on main. Retained them rather than creating replacement layers.
- Parallel JavaScript emergency screening, standalone assistant HTML, and local provider variants exist on unmerged branches, not the main runtime. They were not blindly copied into main or deleted remotely.
- Replaced duplicated local setup instructions with links to the root README. Retained specialized API references and deployment instructions. Moved the old handoff to `docs/history/` with an explicit historical label; its original path remains a link.

## Backend review findings

Patient routes use verified identities and ownership-filtered lookups; caregiver access is relationship/scoped and version-checked. Sessions close through the dependency context manager. Integrity failures return 409 and other database failures return sanitized 503 responses. List APIs are bounded and ordered. Medication summaries batch related queries rather than loading per medication. Existing migrations retain uniqueness and recovery indexes. No measured bottleneck justified a schema or query rewrite in this cleanup.

Important limits: frontend pagination is incomplete; chat detail loads the full stored conversation; private-schema ORM routing is not Alembic private-schema targeting; caregiver invitations are demo-only. These are follow-up work, not claims of completed optimization. Medical rules were not changed, newly invented, or labeled clinically validated.

## File changes

Added nine page modules, two shared component modules, `hooks/useWindow.ts`, `services/presentation.ts`, and an alert presentation test. Modified App imports and reduced Pages to compatibility exports. Updated root/backend/frontend setup and integration docs. Added this report and a historical handoff copy; retained a forwarding note at the old handoff path. No backend runtime files, migrations, lockfiles, workflows, launcher scripts, deployment config, or patient data were removed or altered.

## Verification

- Clean `npm ci`: passed (214 packages).
- Frontend: **16 tests passed across 6 files**; production build and TypeScript passed, including an extra `--noUnusedLocals` check.
- `npm audit`: **0 vulnerabilities**, including development dependencies.
- Fresh isolated SQLite migration upgrade/check: **0005 head; no new upgrade operations**.
- Backend full suite: **103 passed, 1 skipped** (PostgreSQL-only test), with one upstream Starlette/httpx deprecation warning.
- Existing tests exercise patient/caregiver isolation, revocation, medication/check-in corrections, risk/history, provider fallback, persistence, demo login and frontend unreachable-service handling.
- Default Windows pytest temp directory denied access. Verification uses a newly created workspace `.test-tmp` parent and a dedicated `--basetemp`; no test assertions were weakened.
- PostgreSQL/Docker tools were not available locally. The private-schema PostgreSQL test is conditional; the existing PostgreSQL workflow must validate it in CI. No hosted database was used for testing.
- No browser end-to-end test suite is configured in the repo. Component tests/build are not evidence of full hosted browser workflows.

## Remaining work (priority order)

1. Validate private-schema migration targeting before any future hosted schema changes; preserve established hosting settings.
2. Reconcile PR #8 and selectively integrate PR #7 reminders with ownership, migration and provider-failure tests. Keep independent clinical review requirements and prototype labels.
3. Add complete frontend pagination and browser end-to-end tests; bound large chat history retrieval without breaking current clients.
4. Review remaining lifecycle changes from api-reliability and unique emergency branch rules with their authors. Do not treat overlapping behavior as permission to delete branches.
5. Continue improving dense JSX formatting when touching individual features; this cleanup intentionally avoids a repository-wide formatting diff.
