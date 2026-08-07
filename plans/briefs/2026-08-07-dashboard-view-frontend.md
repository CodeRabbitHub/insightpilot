# Brief — dashboard-view-frontend

Date: 2026-08-07
Milestone: M6 Dashboard

Goal:
Add a read-only Dashboard view to the React app that fetches
`GET /api/dashboards/1` and renders each pinned card's title and chart.

Constraints:
- No new dependencies (ARCHITECT.md stack decision) — no router library.
  Add the dashboard as a third top-level view in `App.tsx`, switched with
  the same local-`useState` view-toggle pattern already used for
  `selectedId`/`ConversationList`/`ConversationDetailView` — no routing.
- Reuse `ChartView.tsx` unchanged (`chartSpec`, `rows` props) to render
  each card's `chart_spec_json` + `rows`. Do not modify `ChartView.tsx`.
- Dashboard id hardcoded to `1` (the seeded Overview dashboard) — no
  dashboard picker, no multi-dashboard UI.
- Read-only this slice: no rename input, no delete button, no re-run
  button, no drag-to-reposition — title + chart per card only.
- Match established frontend conventions: Tailwind utility classes
  inline, plain function components with inline-destructured typed
  props, local component state only (`SqlDetails.tsx`/`FollowUpChips.tsx`
  as the pattern to match).
- No backend changes — `GET /api/dashboards/{id}` already exists
  (`app/main.py:358`, `DashboardDetail` response model) and stays
  untouched.

Inputs:
- `app/main.py`'s `GET /api/dashboards/{id}` — response shape
  `DashboardDetail` (`id`, `name`, `created_at`, `cards: []`), each card a
  `DashboardCardWithRows` (`id`, `dashboard_id`, `title`, `question_text`,
  `sql_text`, `chart_spec_json`, `position`, `created_at`, `rows`).
- `web/src/api.ts`'s `fetchConversation`/`fetchConversations` — the
  fetch-plus-throw-on-`!response.ok` pattern to mirror for a new
  `fetchDashboard(id)`.
- `web/src/components/ChartView.tsx`'s existing props contract
  (`chartSpec`, `rows`) — call it once per card, unchanged.
- `web/src/App.tsx`'s `useEffect`-driven fetch-on-mount +
  `loading`/`error` state pattern (the `fetchConversations` effect) as the
  pattern for the new dashboard fetch.
- Real seeded data: Overview dashboard (id 1) already has real pinned
  cards from prior sessions' shipping proofs — usable as fixture data for
  the done-check without pinning a new one.

Outputs:
- `web/src/api.ts`: `fetchDashboard(id)` plus `DashboardDetail`/
  `DashboardCardWithRows`-mirroring TypeScript interfaces (matching the
  backend Pydantic field names exactly, snake_case as the wire format
  already is elsewhere in this file).
- New `web/src/components/DashboardView.tsx`: renders loading/error
  states, then one block per card (title heading + `ChartView`), given a
  `DashboardDetail`.
- `web/src/App.tsx`: a top-level nav control ("Conversations" /
  "Dashboard" tabs/buttons) that switches which top-level view is shown,
  wiring the dashboard view to `fetchDashboard(1)` on mount.

Done-check:
Start the dev server (API + `npm run dev`), open the app in a browser,
click into the Dashboard view, and take a Playwright screenshot showing
at least one real pinned card's title and its rendered chart from the
real `GET /api/dashboards/1` response.

Out-of-scope:
- Rename/delete/re-run card actions and their UI controls — separate
  later slices, one action at a time.
- Drag-to-reposition.
- Any dashboard picker or multi-dashboard UI.
- Any SQL/explanation viewer on dashboard cards — the dashboard response
  has no `analysis`/`explanation` field, unlike chat messages, so
  `SqlDetails.tsx` does not apply here.
- Any backend change.
