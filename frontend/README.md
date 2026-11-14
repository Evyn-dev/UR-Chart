# UR Chart frontend

React 19, TypeScript, Vite, and CSS/Tailwind. Follow the [root setup guide](../README.md#local-setup) and [deployment guide](DEPLOY_VERCEL.md).

`App.tsx` owns routing and demo entry; `hooks/session.tsx` owns the current session. Each route has its own module in `pages/`. `Pages.tsx` retains compatibility exports for existing integrations; new code should import individual pages. Shared medication dose controls live in `components/DaySummary.tsx`; layouts, notices, and the lazy chart boundary live in `components/RecoveryUI.tsx`.

All HTTP requests use `services/client.ts`. Feature services and `types/api.ts` define the frontend API boundary. Shared date windows use the patient's timezone through `hooks/useWindow.ts`. Alert ordering and display helpers live in `services/presentation.ts`. Medical screening remains in Python, not browser code.

From this directory: `npm ci`, `npm run dev`, `npm test`, `npm run build`, `npm audit`. The build includes TypeScript checking. Component tests include caregiver revocation, login modes, unreachable API behavior, dates, and feature availability.

The unmerged voice/local-AI work in PR #8 should integrate into `pages/AssistantPage.tsx`; preserve the shared chat client and backend ownership checks. See the [branch inventory](../docs/REPOSITORY_CLEANUP.md).
