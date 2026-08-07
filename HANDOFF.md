# Handoff

Date: 2026-08-08
Slice just completed: plans/briefs/2026-08-07-dashboard-card-rename-button.md
  + plans/logs/2026-08-07-dashboard-card-rename-button.md
  (commit 41c0153, capture 9a302a6)

## State of the work

- **`web/src/api.ts` gains `renameCard(id: number, title: string): Promise<DashboardCardDetail>`**:
  `fetch` with `method: 'PATCH'`, `headers: {'Content-Type': 'application/json'}`,
  `body: JSON.stringify({ title })`, against `/api/cards/{id}` — throws
  `Error` with the route + status on failure, resolves with the parsed
  `DashboardCardDetail` body on success. `DashboardCardDetail` is a new
  interface matching the PATCH route's real response shape (no `rows`
  field); `DashboardCardWithRows` now `extends DashboardCardDetail` rather
  than hand-duplicating its 7 shared fields, mirroring the backend's own
  `DashboardCardWithRows(DashboardCardDetail)` inheritance
  (`app/main.py:77-90`).
- **`web/src/components/DashboardView.tsx` gains a per-card "Rename"
  button** (`text-sm text-gray-700 hover:underline`, between Re-run and
  Delete) wired to `handleRename(cardId, currentTitle)`: calls
  `window.prompt('New title', currentTitle)` (native browser API, zero
  new dependency); a `null` result (cancel) or a result that trims to
  empty is a no-op — no request sent; otherwise calls
  `renameCard(cardId, trimmed)` and, on success, merges only `title` from
  the response into that one card's state via a new `updateCard(cardId,
  merge)` helper (never swapping the whole card object, since the PATCH
  response has no `rows` and would otherwise blank the chart).
- **The three per-action error states (`deleteError`/`rerunError`/
  `renameError`) were consolidated into one shared `actionError` state**
  — a deliberate deviation from this slice's own brief, which had
  literally specified a fourth dedicated `renameError` state. The no-slop
  reviewer flagged the pre-consolidation state as the third occurrence of
  an identical error-state/handler/button shape (exactly the no-slop
  checklist's "third occurrence means extract" trigger); presented to the
  user as an explicit choice between brief-literal compliance and fixing
  the duplication inline, and the user chose to consolidate. `handleDelete`,
  `handleRerun`, and `handleRename` all now clear/set `actionError`
  instead of three separate states; `handleRerun`/`handleRename` share the
  new `updateCard` helper (`handleDelete`'s filter-based removal is a
  different shape and was left as its own function).
- **This is the second time this project has fixed a third-occurrence
  duplication inline rather than deferring it** (the first was the rerun
  slice's `mockFetchOnce` test-helper extraction). Promoted to a standing
  rule per direct sign-off: `templates/no-slop.md`'s Duplication section
  gains a line requiring this going forward, even when a brief's
  Constraints spelled out the un-extracted, brief-literal version — the
  no-slop reviewer should flag the deviation to the user, not silently
  defer or silently override the brief.
- **Real-server + real-browser proof**: created a real pinned card via
  curl (id 2298, then recreated as 2299 after 2298's placeholder SQL
  referenced nonexistent tables and had to be fixed), drove real headless
  Chromium (Playwright, transient — not in `package.json`/lockfile,
  installed ad hoc into the session's scratchpad directory since `npx -p`
  does not resolve ESM `import`s) to the running Vite dev server, clicked
  the card's "Rename" button, auto-accepted the native `window.prompt`
  dialog via Playwright's `page.on('dialog')`. Proof card deleted
  afterward; dashboard 1 confirmed back to exactly 7 cards (all
  pre-existing pollution from prior sessions), zero new pollution added
  by this slice.
- **No-slop review, two passes** (record:
  `artifacts/reviews/2026-08-07-dashboard-card-rename-button.md`): pass 1
  caught the `DashboardCardDetail`/`DashboardCardWithRows` field
  duplication and the error-state triplication (both fixed, see above).
  Pass 2 confirmed both landed, caught two stale-naming nits (a test-file
  comment and a test description still named the removed `deleteError`/
  `renameError` states — both reworded to `actionError`), and judged the
  residual identical one-line `.catch((e) =>
  setActionError(errorMessage(e)))` across all three handlers an accepted
  exception (further extraction would be over-abstraction for one line).
  Zero unresolved findings at commit time.
- **New tests added, still cannot execute**: new
  `web/tests/api.renameCard.test.ts` (11 cases) and an extended
  `web/tests/DashboardView.test.tsx` (button presence, prompt default
  value, cancel/empty/whitespace-only no-op, successful rename's
  title-only merge proven via the existing `ChartView` call-through spy,
  sibling isolation, failed-rename error surfacing, no extra
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
✓ built in 2.26s
```
Real-server shipping proof (Gate 2 check 5, run against the final diff):
created proof card 2299 via `POST /api/dashboards/1/cards` → real headless
Chromium opened the Dashboard tab, clicked card 2299's Rename button,
auto-accepted the native prompt with "Renamed by Playwright proof v2" →
network trace confirmed
```json
{
  "requests": [{"method":"PATCH","url":"http://localhost:8000/api/cards/2299",
                "postData":"{\"title\":\"Renamed by Playwright proof v2\"}","status":200}],
  "consoleErrors": [],
  "headingsBeforeCount": 8, "headingsAfterCount": 8,
  "canvasCount": 1, "hasErrorText": false
}
```
→ proof card deleted (`DELETE /api/cards/2299` → 204) → fresh
`GET /api/dashboards/1` confirmed 7 cards remain, all pre-existing. Zero
DB pollution left by this slice.

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
    `docker compose up -d` before assuming a code regression.
  - The dev Postgres `dashboards`/`dashboard_cards` tables have
    accumulated leftover proof/test cards from prior sessions' real-
    server shipping proofs (harmless; 7 cards confirmed pre-existing as
    of this slice, still worth a cleanup pass eventually).
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
- New this slice:
  - `get_dashboard`'s `ORDER BY DashboardCard.position` (`app/main.py:380`)
    has no secondary sort key, so cards with equal `position` (all 7
    pre-existing dev cards currently have `position: 0`) sort in
    whatever order Postgres happens to return ties — worth confirming is
    stable enough for the drag-to-reposition slice, or fixing with a
    secondary `id`/`created_at` tiebreaker if it isn't.
  - Playwright (transient, per this project's established pattern for
    real-browser proofs) cannot be resolved via `npx -p playwright node
    script.mjs` because `npx -p` doesn't add the package to Node's ESM
    resolution path — installing it into a throwaway `npm init` directory
    (e.g. the session scratchpad) and running the script from there does
    work. Worth remembering for the next slice's shipping proof to avoid
    re-discovering this.

## Next slice (the brief, written NOW while context is hot)

Goal:
Let a user reorder pinned cards by dragging them in `DashboardView.tsx`,
persisting the new order through the already-shipped
`PATCH /api/cards/{id}` (`position` field).

Constraints:
- Frontend only (`web/src/api.ts` + `web/src/components/DashboardView.tsx`)
  — no backend changes; `PATCH /api/cards/{id}` and
  `get_dashboard`'s `ORDER BY DashboardCard.position` (`app/main.py:380`)
  already exist and are untouched.
- No new dependency (per ARCHITECT.md's excluded-deps list and CLAUDE.md's
  standing rule) — use the browser-native HTML5 drag-and-drop API
  (`draggable` attribute + `onDragStart`/`onDragOver`/`onDrop` handlers on
  each card's `<li>`), not a drag-and-drop library.
- `web/src/api.ts` gains `repositionCard(id: number, position: number): Promise<DashboardCardDetail>`,
  mirroring `renameCard`'s PATCH+JSON-body shape exactly but sending
  `{ position }` instead of `{ title }`. Do not generalize `renameCard`/
  `repositionCard` into one shared `patchCard(id, {title?, position?})`
  in this slice — that's only two call sites, not the third-occurrence
  trigger `templates/no-slop.md` now codifies; revisit if a third PATCH
  variant appears.
- On drop, reorder the local `dashboard.cards` array immediately
  (optimistic UI), then call `repositionCard` for every card whose
  position changed, renumbering sequentially (0, 1, 2, ...) to match
  `get_dashboard`'s sort key. Reuse the existing `actionError` state for
  failures (consistent with delete/rerun/rename, per the no-slop-promoted
  consolidation this slice shipped) — on any `repositionCard` failure,
  revert the local reorder rather than leaving the UI showing an order
  that didn't actually persist.
- Match the existing file's style: functional component, `useState`,
  Tailwind utility classes consistent with the file's existing action
  buttons/cards.

Inputs:
- `web/src/components/DashboardView.tsx` (current, post rename-slice) —
  each card's `<li>` is what becomes `draggable`.
- `web/src/api.ts`'s `renameCard` (PATCH + JSON body + parsed
  `DashboardCardDetail` response) as the pattern `repositionCard` mirrors
  exactly, just swapping the body field.
- `app/main.py`'s `patch_dashboard_card` route (`app/main.py:416-437`) and
  `get_dashboard` (`app/main.py:363-399`, specifically the
  `.order_by(DashboardCard.position)` at line 380) — the contract
  `repositionCard` calls against and the sort behavior the new position
  values must satisfy; no backend inspection beyond confirming this
  contract, since both routes are out of scope.
- `web/tests/DashboardView.test.tsx` and `web/tests/api.renameCard.test.ts`
  (existing, as the patterns to mirror), plus the shared
  `web/tests/helpers/mockFetch.ts` fetch-stub helper.

Outputs:
- `web/src/api.ts` gains `repositionCard(id: number, position: number): Promise<DashboardCardDetail>`.
- `web/src/components/DashboardView.tsx`'s cards become drag-reorderable;
  dropping a card in a new slot reorders the rendered list immediately
  and persists new sequential `position` values for every card whose
  position changed; a failed persist reverts the local order and shows
  an error via `actionError`.
- Test coverage for: dragging a card to a new slot reorders the local
  list optimistically; `repositionCard` is called with the correct
  sequential position for each affected card (not just the dragged one,
  if reordering shifts siblings); a failed `repositionCard` call reverts
  the local order and surfaces an error without corrupting unrelated
  card data; no extra `fetchDashboard` call on any path. (Same standing
  gap as every prior frontend test file: cannot execute this session, no
  vitest/jest wired in yet.)

Done-check:
`cd web && npm run build` (type-checks + builds cleanly) plus a real-server
shipping proof: create at least 2 real pinned cards with distinct
positions via curl, load the Dashboard tab in a real browser (Playwright
dispatching `dragstart`/`dragover`/`drop` events — remember this session's
scratchpad-install workaround for resolving the `playwright` package, or
manual), drag one card to a new slot, confirm `PATCH /api/cards/{id}`
requests fire with the correct new `position` values, confirm a fresh
`GET /api/dashboards/1` reflects the new order, and confirm no console
errors. Delete proof cards afterward.

Out-of-scope:
- Any backend change to `PATCH /api/cards/{id}` or `get_dashboard`'s sort.
- Touch-screen/mobile drag support — the native HTML5 drag-and-drop API
  is desktop-mouse-only; a known limitation, not fixed here.
- Generalizing `renameCard`/`repositionCard` into one shared `patchCard`
  function — explicitly deferred per this brief's Constraints until a
  third PATCH variant exists.
- Adding a secondary sort key to `get_dashboard`'s `ORDER BY` even if the
  all-zero `position` tie observed this session turns out to matter —
  flag it if it does, fix it in its own slice, don't fold it into this one.
- The orphaned `plans/logs/2026-08-07-run-dashboard-card-endpoint.md`
  cleanup — unrelated file, separate housekeeping slice.
- Wiring up a frontend test runner (vitest/jest) — a new dependency,
  needs its own explicit ask per CLAUDE.md's standing rules.
