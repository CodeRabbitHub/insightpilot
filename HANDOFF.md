# Handoff

Date: 2026-08-07
Slice just completed: plans/briefs/2026-08-07-card-to-detail-refactor.md
  + plans/logs/2026-08-07-card-to-detail-refactor.md
  (commit a50a484)

## State of the work

- **`app/main.py` gains `_card_to_detail(card: DashboardCard) ->
  DashboardCardDetail`**, a private module-level helper placed next to
  `_persist_exchange` (matching this file's existing leading-underscore
  naming convention). It replaces the same 7-field
  `DashboardCardDetail(id=..., dashboard_id=..., ...)` construction that
  was previously duplicated by hand in four routes.
- **All four call sites now use it**: `create_dashboard_card` and
  `patch_dashboard_card` return `_card_to_detail(card)` directly;
  `get_dashboard` and `run_dashboard_card` build their
  `DashboardCardWithRows` via
  `DashboardCardWithRows(**_card_to_detail(card).model_dump(), rows=rows)`
  — `get_dashboard` previously had its own separate 8-field
  `DashboardCardWithRows(...)` construction and now matches
  `run_dashboard_card`'s pre-existing pattern instead.
- **Zero behavior change, confirmed two ways**: `tests/test_api_dashboard_cards.py`'s
  full 76-test suite passes unchanged (same count, same assertions), and a
  fresh real-server proof exercised create → patch → run → get_dashboard →
  delete on a real pinned card, all four routes returning the same field
  shapes as before the refactor.
- **No-slop review clean** on `app/main.py`: extraction complete at all
  four sites (no old inline block left anywhere), naming/consistency match
  the file's existing helpers, nothing touched outside the four named
  routes. Full record: `artifacts/reviews/2026-08-07-card-to-detail-refactor.md`.
- Test-writer subagent was deliberately skipped this slice (not the usual
  step 4): the brief's own Out-of-scope ruled out new test-behavior, and
  the existing 76 tests already assert exact response shapes on all four
  touched routes — recorded as this slice's "rejected or changed" judgment
  call, not an oversight.
- **No frontend, schema, or dependency changes.**

## Proof

```
$ .venv/Scripts/python -m unittest discover -s tests -p "test_api_dashboard_cards.py" -v
...
Ran 76 tests in 33.290s

OK
```
Real-server shipping proof (Gate 2 check 5): created card 2292 on
dashboard 1 (`POST /api/dashboards/1/cards`, real 3-row state-aggregate
SQL) → patched its title (`PATCH /api/cards/2292`) → ran it
(`POST /api/cards/2292/run`, returned the same 3 real rows) → confirmed it
appears in `GET /api/dashboards/1` with an identical shape → deleted it
(`DELETE /api/cards/2292` → 204) → confirmed gone (`POST .../run` → 404
"card not found"). Zero DB pollution left by this slice.

## Open questions / known issues

- Carried over, unchanged from the previous handoff (still true, still
  unaddressed):
  - Frontend unit tests (5 files) still exist but cannot execute — no
    vitest/jest wired into `web/package.json`. Adding one is a new
    dependency.
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
    server shipping proofs (harmless, but worth a cleanup pass
    eventually). This slice's own proof card (2292) was deleted before
    finishing, so it added zero new pollution.
  - A `uvicorn` dev server left running from a prior session (bound on
    port 8000) is still up and was reused for this slice's shipping
    proofs rather than restarted — if a future session's own
    `uvicorn --reload` fails with "only one usage of each socket
    address," that's why.
  - Card actions in the UI (rename input, delete button, re-run button,
    drag-to-reposition) still don't exist — the backend routes for all
    four already exist; this is the seed for the next brief below.
- New this slice:
  - `plans/logs/2026-08-07-run-dashboard-card-endpoint.md` sits untracked
    in the working tree (confirmed still untracked as of this slice's
    gate) — a leftover from a session two slices back whose "Capture:
    run-dashboard-card-endpoint slice log" commit was apparently skipped
    (visible in `git log`: commit `0a025a0`, the route's own code, is
    followed directly by `6f04d37`, the *next* slice's code, with no
    intervening capture commit). This slice's no-slop reviewer flagged it
    as pre-existing and out of this slice's scope (backend-only,
    `app/main.py` only), so it was left untouched rather than folded in
    silently. Worth a deliberate small cleanup commit in a future session
    (`git add` + commit that one file, or fold it into a
    housekeeping slice) rather than continuing to carry it forward
    unaddressed.
  - This handoff's own rewrite, plus `plans/logs/2026-08-07-card-to-
    detail-refactor.md` and the hook-appended `plans/logs/_auto-
    capture.md`, are committed together in this slice's own capture
    commit (unlike the `run-dashboard-card-endpoint` gap above) — so this
    slice does not add to the uncommitted-state pile.

## Next slice (the brief, written NOW while context is hot)

Goal:
Add a delete button to each pinned card in `DashboardView.tsx` that calls
the already-shipped `DELETE /api/cards/{id}` and removes that card from
the rendered list on success.

Constraints:
- Frontend only (`web/src/api.ts` + `web/src/components/DashboardView.tsx`)
  — no backend changes; `DELETE /api/cards/{id}` already exists and is
  untouched.
- `web/src/api.ts` gains a `deleteCard(id: number): Promise<void>`
  function following `fetchDashboard`'s existing throw-on-`!response.ok`
  shape (see `api.ts` lines 62-68) — `fetch` with `method: 'DELETE'`,
  no request body, throws `Error` with the route + status on failure,
  resolves with nothing (`void`) on the real 204 empty-body success case
  (do not attempt to parse a JSON body from a 204 response).
- The button removes the card from `DashboardView`'s local `dashboard`
  state optimistically-on-success only (call `deleteCard`, and on success
  filter the deleted id out of `dashboard.cards` via `setDashboard`; on
  failure, leave the card in place and surface the error via the
  existing `error` state / `errorMessage(e)` helper, not a silent
  no-op) — no full `fetchDashboard` refetch needed for this one action.
- No new dependency, no router change, no confirmation dialog (out of
  scope, see below).
- Match the existing file's style: functional component, `useState`,
  no new libraries, Tailwind utility classes consistent with the
  existing `<h3>`/`<p>` classes in this file.

Inputs:
- `web/src/components/DashboardView.tsx` (current, 36 lines) — the `<li>`
  per card at lines 29-33 is where the button goes, inside the same `<li>`
  as the card's title and `ChartView`.
- `web/src/api.ts`'s `fetchDashboard` (lines 62-68) as the pattern to
  mirror for `deleteCard`; `errorMessage` (line 3) already exported and
  used by `DashboardView.tsx`.
- `app/main.py`'s `delete_dashboard_card` route (204 on success, 404 with
  `{"detail": "card not found"}` on an unknown id) — the contract
  `deleteCard` calls against; no backend inspection beyond confirming this
  contract, since the route itself is out of scope.
- `web/tests/DashboardView.test.tsx` (existing, 15 tests) — extend in
  place for the new button; same known limitation as every other frontend
  test file (no vitest/jest runner wired into `web/package.json`, so these
  cannot execute this session either — note this explicitly in the log
  rather than claiming a pass).

Outputs:
- `web/src/api.ts` gains `deleteCard(id: number): Promise<void>`.
- `web/src/components/DashboardView.tsx`'s per-card `<li>` gains a
  "Delete" button; clicking it calls `deleteCard(card.id)` and removes
  that card from the rendered list on success, or shows an error and
  leaves the card in place on failure.
- Test coverage added to `web/tests/DashboardView.test.tsx` for: button
  present per card, successful delete removes only that card from the
  list (siblings untouched), failed delete leaves the card in place and
  surfaces an error.

Done-check:
`cd web && npm run build` (type-checks + builds cleanly) plus a real-server
shipping proof: create a real pinned card via `curl`, load the Dashboard
tab in a real browser (Playwright or manual), click its Delete button,
confirm it disappears from the rendered page, and confirm via a fresh
`GET /api/dashboards/{id}` curl that the row is genuinely gone server-side
— not just removed from the DOM.

Out-of-scope:
- Rename input, re-run button, and drag-to-reposition — the other three
  card actions flagged as missing UI; each is its own future slice.
- A confirmation dialog/modal before deleting — not requested, and this
  brief's Goal is the single action, not a UX safety net around it.
- Any backend change to `DELETE /api/cards/{id}` itself.
- The orphaned `plans/logs/2026-08-07-run-dashboard-card-endpoint.md`
  cleanup noted above — unrelated file, separate housekeeping slice.
