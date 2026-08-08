# Brief — dashboard-strictmode-fetch-guard

Date: 2026-08-08
Milestone: M6 Dashboard (card actions)

Goal:
Fix `DashboardView.tsx`'s mount effect so React 18 StrictMode's dev-only
double-invoke can never let a stale duplicate `fetchDashboard` response
overwrite newer state.

Constraints:
- Touch only `web/src/components/DashboardView.tsx`'s existing mount
  `useEffect` (currently lines ~26-32) — no backend change, no new
  dependency, no change to any other part of the component (the action
  handlers — delete/rerun/rename/drag — and `actionError` are unrelated
  to this race and stay untouched).
- Use the standard ignore-flag cleanup pattern (React's own documented
  fix for exactly this class of race, from "Fetching data with
  Effects"): a local `ignore` boolean, `false` at the start of each
  effect invocation, flipped to `true` in the effect's returned cleanup
  function, checked before each of `setDashboard`/`setError`/
  `setLoading` fires in the `.then`/`.catch`/`.finally` handlers — so a
  stale invocation's eventual resolution can never mutate state once
  that invocation's own cleanup has already run.
- Do not switch to `AbortController` instead — functionally equivalent
  for this specific bug, but would require changing `fetchDashboard`'s
  signature to accept a signal, a larger surface change than this fix
  needs.
- No visible behavior change for the normal path: a real mount (in
  production, where StrictMode's double-invoke doesn't happen and
  `dashboardId` never changes in this app) must still show exactly one
  loading → loaded (or loading → error) transition, identical to today.

Inputs:
- `web/src/components/DashboardView.tsx`'s current mount effect:
  ```ts
  useEffect(() => {
    setLoading(true)
    setError(null)
    fetchDashboard(dashboardId)
      .then(setDashboard)
      .catch((e: unknown) => setError(errorMessage(e)))
      .finally(() => setLoading(false))
  }, [dashboardId])
  ```
- HANDOFF.md's "State of the work" section (prior slice), which documents
  the exact bug trace from that session's debugging (two real
  `fetchDashboard` GETs fire at mount under StrictMode; whichever
  resolves last wins and silently overwrites any local state changed in
  the meantime, since `get_dashboard`'s real per-card SQL re-execution
  makes response latency real and variable).
- `web/src/main.tsx` — confirms `<StrictMode>` wraps the app, which is
  why this only reproduces in dev, not in a production build.

Outputs:
- The same mount effect, with the ignore-flag pattern added exactly as
  described in Constraints.
- Test coverage (new, from this brief — same standing execution gap as
  every other frontend test in this repo, no vitest/jsdom wired in yet)
  proving: a `fetchDashboard` promise that resolves AFTER the effect's
  cleanup has run does not call `setDashboard`/`setError`/`setLoading`;
  the normal single-invocation path (fetch resolves, no cleanup in
  between) is completely unaffected — loading → loaded and loading →
  error both still work exactly as before.

Done-check:
`cd web && npm run build` (type-checks and builds cleanly) plus a
real-server shipping proof under the dev server (StrictMode active):
reproduce the failure mode first on the pre-fix code (drag a card
immediately after page load, with no settle-wait, and confirm it still
reverts a few seconds later — establishing the bug is real and
reproducible), then confirm the same drag on the fixed code survives past
5+ seconds without reverting. Confirm no console errors on either run.

Out-of-scope:
- Any other part of `DashboardView.tsx` (action handlers, `actionError`,
  drag logic) — untouched, this is a mount-effect-only fix.
- Switching to `AbortController` — the ignore-flag pattern is the
  minimal fix per this brief's Constraints.
- Auditing or fixing this same shape anywhere else in the codebase, even
  if it exists elsewhere — confirm no other effect in this file has the
  issue while implementing, but a repo-wide sweep for the same pattern
  is its own separate slice if warranted.
- Making `dashboardId` a dynamic, routing-driven prop — unrelated to
  this bug, still a hardcoded `1` throughout the app.
- The DB-drift-on-partial-failure tradeoff from the drag-reposition
  slice — a separate, already-decided, accepted limitation, not a bug.
- The orphaned `plans/logs/2026-08-07-run-dashboard-card-endpoint.md`
  cleanup — unrelated file, separate housekeeping slice.
