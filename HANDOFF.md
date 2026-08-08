# Handoff

Date: 2026-08-08
Slice just completed: plans/briefs/2026-08-08-dashboard-card-drag-reposition.md
  + plans/logs/2026-08-08-dashboard-card-drag-reposition.md
  (commit 1cc5574, capture c44ee8e)

## State of the work

- **`web/src/api.ts` gains `repositionCard(id: number, position: number): Promise<DashboardCardDetail>`**:
  identical shape to `renameCard` — `fetch` with `method: 'PATCH'`,
  `headers: {'Content-Type': 'application/json'}`,
  `body: JSON.stringify({ position })`, against `/api/cards/{id}` —
  throws `Error` with the route + status on failure, resolves with the
  parsed `DashboardCardDetail` body on success. No new type needed.
- **`web/src/components/DashboardView.tsx`'s cards are now
  drag-reorderable** via the native HTML5 drag-and-drop API (no library,
  per ARCHITECT.md's excluded-deps list): each card's `<li>` is
  `draggable`, with `onDragStart` (stores the dragged card's id in new
  `draggedCardId` state, and calls `e.dataTransfer.setData(...)` —
  required by Firefox to permit starting a drag at all), `onDragOver`
  (`e.preventDefault()`, required to allow a drop), and `onDrop`
  (`e.preventDefault()` then `handleDrop(card.id)`). `handleDrop`
  splices the dragged card out of the local array and back in at the
  target's index (standard list drag-reorder semantic), renumbers
  every card's `position` sequentially (0, 1, 2, ...), applies that
  optimistically to `dashboard.cards`, then calls the new
  `repositionCard` for every card whose slot's occupant actually
  changed (not only the dragged card — shifting the dragged card
  shifts every card between its old and new index too). Reuses the
  existing shared `actionError` state; on any `repositionCard`
  rejection, reverts `dashboard.cards` back to the exact pre-drag
  array.
- **Accepted tradeoff, decided by the user**: a partial `repositionCard`
  failure (some of the `Promise.all`'d calls succeed, one rejects) can
  leave the backend holding some already-persisted new positions while
  the client reverts its local view to the pre-drag order — the two can
  drift until the next full page reload. Fixing this properly needs
  either a backend transactional/batch endpoint (out of scope) or
  frontend compensating rollback PATCH calls (adds real complexity and
  its own failure modes). Presented as an explicit choice; the user
  chose to accept it as a documented known limitation rather than add
  rollback logic the brief never asked for. First occurrence of this
  specific tradeoff in the project.
- **No `onDragEnd` handler**: if a drag is released outside any card, no
  `onDrop` fires and `draggedCardId` stays set until the next
  `onDragStart` overwrites it. No observed functional bug (the state is
  write-only, read only inside `onDrop`) — a deliberate, documented
  omission rather than defensive code for an unobserved failure mode.
- **Discovered, NOT fixed (now the next slice): a pre-existing React
  StrictMode double-fetch race** in `DashboardView`'s original mount
  `useEffect` (from an earlier slice, unrelated to this one's new
  code). Under `npm run dev`'s `<StrictMode>` (`web/src/main.tsx`), the
  effect body runs twice at mount, firing two real `fetchDashboard`
  HTTP GETs; whichever resolves LAST wins and calls `setDashboard`,
  even if that's seconds later (this endpoint re-executes every pinned
  card's SQL on every call, so latency is real and variable —
  `app/main.py`'s `get_dashboard` docstring). This silently overwrote a
  completed drag reorder mid-proof and cost real debugging time this
  session before being correctly identified as pre-existing and
  unrelated to the new drag code (confirmed by reproducing it with a
  settle-wait workaround, and by temporary debug logging showing two
  separate `fetchDashboard` resolutions, the second landing ~2s after
  the first, with no corresponding second effect-fire log — i.e. it's
  the FIRST invocation's request resolving late, not a second effect
  run). Not observable in a production build (StrictMode's double-
  invoke is dev-only, and `dashboardId` never changes in this app, so
  production only ever fires the effect once).
- **No-slop review** (record:
  `artifacts/reviews/2026-08-08-dashboard-card-drag-reposition.md`): one
  pass. Fixed: added a one-line comment explaining why
  `dataTransfer.setData` is called despite nothing reading it back
  (Firefox drag-start requirement). Accepted as documented exceptions:
  the DB-drift tradeoff above, and the missing `onDragEnd` handler.
  Zero unresolved findings at commit time.
- **New tests added, still cannot execute**: new
  `web/tests/api.repositionCard.test.ts` (11 cases, mirroring
  `api.renameCard.test.ts`) and an extended `web/tests/DashboardView.test.tsx`
  (optimistic reorder before persistence settles, `repositionCard`
  called with the correct renumbered position for every shifted
  sibling — not just the dragged card, no call for an unaffected
  sibling, full revert + `actionError` on any persist failure, no extra
  `fetchDashboard` call on any path). Same standing gap as every other
  frontend test file: no vitest/jsdom wired into `web/package.json` yet.
- **No backend, schema, or dependency changes.**

## Proof

```
$ cd web && npm run build
> web@0.0.0 build
> tsc -b && vite build

vite v8.2.0 building client environment for production...
✓ 628 modules transformed.
✓ built in 844ms
```
Real-server shipping proof (run against the final diff, after a ~2s
page-settle wait to avoid the StrictMode race described above — what a
real user does naturally by looking at the page before dragging):
created two proof cards via `POST /api/dashboards/1/cards` (id 2305
"Drag proof First" position 100, id 2306 "Drag proof Second" position
101) → headless Chromium (Playwright, scratchpad-installed, not added to
`web/package.json`) dispatched real `dragstart`/`dragover`/`drop` events
(each its own round-trip, sharing one `DataTransfer`, to match real drag
timing) dragging "Drag proof Second" onto "Drag proof First"'s slot:
```json
{
  "headingsBefore": ["Drag proof First", "Drag proof Second"],
  "headingsAfter": ["Drag proof Second", "Drag proof First"],
  "patchRequests": [
    {"url": "http://localhost:8000/api/cards/2306", "postData": "{\"position\":7}"},
    {"url": "http://localhost:8000/api/cards/2305", "postData": "{\"position\":8}"}
  ],
  "consoleErrors": []
}
```
→ a fresh `GET /api/dashboards/1` (separate from the browser session)
confirmed the persisted order: card 2306 at position 7, card 2305 at
position 8 → proof cards deleted (`DELETE /api/cards/2305`, `/2306` →
204 each) → dashboard 1 confirmed back to exactly 7 cards, all
pre-existing pollution from prior sessions, zero new pollution from this
slice.

## Open questions / known issues

- Carried over, unchanged from the previous handoff (still true, still
  unaddressed):
  - Frontend unit tests still cannot execute — no vitest/jest wired into
    `web/package.json`. Adding one is a new dependency (needs an explicit
    ask per CLAUDE.md).
  - `chart_spec` still has no fixed schema by design
    (`prompts/analyze.md`); `ChartView.tsx`'s alias-resolution approach
    remains the frontend's answer to this.
  - ECharts auto-hides overlapping x-axis category labels under narrow
    container widths — not a bug, unaddressed by design.
  - No charting library styling beyond a single fixed accent color; no
    dark mode; no table-view toggle.
  - Decimal-valued rows still serialize as JSON strings, not numbers, in
    the raw `<pre>` dump (conversations view only).
  - `NullPool` needs re-evaluation under uvicorn's single persistent
    event loop — still flagged in `app/db/session.py`'s own comment.
  - What happens to an already-computed answer when its persistence
    write fails: still a plain 500 / silently truncated SSE stream.
  - `tests/test_seed_idempotency.py`'s own real Postgres deadlock
    (M1-era, unrelated code) remains uninvestigated.
  - Lint/type tooling on the Python side (`ruff`, `mypy`) remains
    unaddressed.
  - A `response.content[0].text`/`ThinkingBlock` bug pattern is fixed
    only in `analyze_answer.py`; `generate_sql.py`, `repair_sql.py`,
    `describe.py` still carry the same fragile assumption.
  - The project's own `.venv` (Python 3.11.15) must be used explicitly
    for backend commands.
  - API base URL is a hardcoded `http://localhost:8000` constant in
    `web/src/api.ts`.
  - `Conversation`'s `user_id` FK to `users` is deliberately omitted —
    `users` doesn't exist yet (F8).
  - `queries` table (PRD §7's fourth `app`-schema table) still doesn't
    exist — not needed until the pipeline-logging slice.
  - Docker Desktop's daemon does not auto-start with this
    machine/session — if a session's done-check fails with a Postgres
    connection refusal on port 5433, start Docker Desktop and run
    `docker compose up -d` before assuming a code regression. (Not
    exercised this session — both the API and web dev servers were
    already running from a prior session and were reused directly.)
  - The dev Postgres `dashboards`/`dashboard_cards` tables have
    accumulated leftover proof/test cards from prior sessions' real-
    server shipping proofs (harmless; still 7 pre-existing cards,
    reconfirmed this session; still worth a cleanup pass eventually).
  - A `uvicorn` dev server left running from a prior session (bound on
    port 8000) is still up and was reused for this slice's shipping
    proofs rather than restarted.
  - A `vite` dev server left running from a prior session (bound on port
    5173) is still up and was reused for this slice's shipping proofs
    rather than restarted.
  - `plans/logs/2026-08-07-run-dashboard-card-endpoint.md` still sits
    untracked in the working tree (a leftover from a session several
    slices back whose capture commit was apparently skipped). Still out
    of every subsequent slice's scope; still worth a deliberate small
    cleanup commit eventually.
  - `get_dashboard`'s `ORDER BY DashboardCard.position` (`app/main.py:380`)
    still has no secondary sort key. Observed informally this session:
    the 7 pre-existing same-position(0) cards' relative order stayed
    consistent across many repeated `GET`s during testing — but this is
    an observation, not a guarantee from Postgres, and still worth a
    secondary `id`/`created_at` tiebreaker if it's ever seen to vary.
  - Playwright (transient, per this project's established pattern for
    real-browser proofs) cannot be resolved via `npx -p playwright node
    script.mjs` because `npx -p` doesn't add the package to Node's ESM
    resolution path — installing it into a throwaway `npm init` directory
    (e.g. the session scratchpad) and running the script from there does
    work; reconfirmed working again this session.
  - Native HTML5 drag-and-drop events dispatched synthetically must each
    go in their own round-trip/turn (not fired back-to-back synchronously
    in one script block) to give React's batching a chance to commit
    state between them — discovered this session while building the
    drag-reposition shipping proof; documented here so the next session
    driving simulated drag events doesn't have to rediscover it.
- New this slice:
  - The React StrictMode double-fetch race described above in "State of
    the work" — now this handoff's next brief.
  - The DB-drift-on-partial-`repositionCard`-failure tradeoff, accepted
    as a documented known limitation (see "State of the work" above) —
    not tracked as a bug to fix, just a known, accepted behavior.

## Next slice (the brief, written NOW while context is hot)

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
- This handoff's "State of the work" section above, which documents the
  exact bug trace from this session's debugging (two real
  `fetchDashboard` GETs fire at mount under StrictMode; whichever
  resolves last wins and silently overwrites any local state changed in
  the meantime, since `get_dashboard`'s real per-card SQL re-execution
  makes response latency real and variable).
- `web/src/main.tsx` — confirms `<StrictMode>` wraps the app, which is
  why this only reproduces in dev, not in a production build.

Outputs:
- The same mount effect, with the ignore-flag pattern added exactly as
  described in Constraints.
- Test coverage (new, from the brief — same standing execution gap as
  every other frontend test in this repo, no vitest/jsdom wired in yet)
  proving: a `fetchDashboard` promise that resolves AFTER the effect's
  cleanup has run does not call `setDashboard`/`setError`/`setLoading`;
  the normal single-invocation path (fetch resolves, no cleanup in
  between) is completely unaffected — loading → loaded and loading →
  error both still work exactly as before.

Done-check:
`cd web && npm run build` (type-checks and builds cleanly) plus a
real-server shipping proof under the dev server (StrictMode active):
reproduce this session's exact failure mode first on the pre-fix code
(drag a card immediately after page load, with no settle-wait, and
confirm it still reverts a few seconds later — establishing the bug is
real and reproducible), then confirm the same drag on the fixed code
survives past 5+ seconds without reverting. Confirm no console errors on
either run.

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
