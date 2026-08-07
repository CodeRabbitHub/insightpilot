# Handoff

Date: 2026-08-07
Slice just completed: plans/briefs/2026-08-07-dashboard-card-delete-button.md
  + plans/logs/2026-08-07-dashboard-card-delete-button.md
  (commit 39f6331)

## State of the work

- **`web/src/api.ts` gains `deleteCard(id: number): Promise<void>`**,
  mirroring `fetchDashboard`'s throw-on-`!response.ok` shape: `fetch` with
  `method: 'DELETE'` against `/api/cards/{id}`, throws `Error` with the
  route + status on failure, resolves with nothing on the real 204
  empty-body success (no `.json()` call on that path).
- **`web/src/components/DashboardView.tsx` gains a per-card "Delete"
  button** (`text-sm text-red-600 hover:underline`, next to each card's
  title) wired to a new `handleDelete(cardId)`: on success it filters the
  deleted id out of local `dashboard.cards` state via `setDashboard` (no
  full `fetchDashboard` refetch); on failure it leaves the card in place
  and surfaces the error.
- **Failure surfacing uses a dedicated `deleteError` state, not the
  page's initial-fetch `error` state** — this was a real bug caught by
  the no-slop gate, not a style choice. `DashboardView` already had
  `if (error) return <p>...</p>` as an early-return guard from the
  initial fetch; reusing that same state for a delete failure would blank
  the *entire* card list instead of leaving the failed card in place,
  directly contradicting the brief. `deleteError` renders inline above
  the `<ul>` with no early return, and carries a one-line comment
  explaining why it's separate from `error`.
- **Zero-refetch confirmed by test, not just by inspection**: a test
  asserts `fetchDashboard` is not called again after a successful
  delete.
- **Real-server + real-browser proof, this session**: created a real
  pinned card via curl, drove real headless Chromium (Playwright,
  already present transiently from a prior session — not in
  `package.json`/lockfile) to the running Vite dev server, clicked
  "Dashboard" then the card's "Delete" button, confirmed the card
  disappeared from the DOM (0 matching headings, 0 console errors), then
  confirmed via a fresh `GET /api/dashboards/1` that the card was
  genuinely gone server-side. Proof script was a transient scratch file,
  deleted after the run.
- **No-slop review, two passes** (record:
  `artifacts/reviews/2026-08-07-dashboard-card-delete-button.md`):
  pass 1 caught the `deleteError`-vs-`error` bug above; pass 2 caught
  that the fix's own justification wasn't written down anywhere and that
  a test-file comment still described the old (buggy) design — both
  fixed with accurate comments before the gate went green.
- **New tests added, still cannot execute**: 12 new cases in
  `web/tests/DashboardView.test.tsx` (button presence, correct-id call,
  sibling isolation on success and failure, no extra refetch, error
  content) and a new `web/tests/api.deleteCard.test.ts` (8 cases,
  mirrors `api.fetchDashboard.test.ts`). No vitest/jsdom wired into
  `web/package.json` yet — same standing gap as every other frontend
  test file in this repo, noted rather than hidden.
- **No backend, schema, or dependency changes.**

## Proof

```
$ cd web && npm run build
> web@0.0.0 build
> tsc -b && vite build

vite v8.2.0 building client environment for production...
✓ 628 modules transformed.
✓ built in 824ms
```
Real-server shipping proof (Gate 2 check 5): `POST /api/dashboards/1/cards`
created card 2294 ("Gate-check proof card: delete button") → real headless
Chromium opened the Dashboard tab, found the card, clicked its Delete
button → `Card headings found after delete (DOM): 0`, `Console errors: []`
→ fresh `GET /api/dashboards/1` confirmed `Card 2294 still present
server-side: false`, `Total cards now: 7`. Zero DB pollution left by this
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
    `docker compose up -d` before assuming a code regression.
  - The dev Postgres `dashboards`/`dashboard_cards` tables have
    accumulated leftover proof/test cards from prior sessions' real-
    server shipping proofs (harmless, but worth a cleanup pass
    eventually). This slice's own proof cards (2293, 2294) were both
    deleted before finishing, so it added zero new pollution.
  - A `uvicorn` dev server left running from a prior session (bound on
    port 8000) is still up and was reused for this slice's shipping
    proofs rather than restarted.
  - **New this slice**: a `vite` dev server was started this session on
    port 5173 (`nohup npm run dev -- --port 5173 --strictPort`,
    disowned) and left running for reuse — if a future session's own
    `npm run dev` fails to bind 5173, that's why; kill it or pick another
    port.
  - `plans/logs/2026-08-07-run-dashboard-card-endpoint.md` still sits
    untracked in the working tree (a leftover from a session several
    slices back whose capture commit was apparently skipped — see
    `git log`: `0a025a0` is followed directly by `6f04d37` with no
    intervening capture commit). Still out of every subsequent slice's
    scope; still worth a deliberate small cleanup commit eventually.
  - Rename input and drag-to-reposition — two of the three remaining
    card actions — still don't exist. (Re-run is next, seeded below.)
- New this slice:
  - The `deleteError`-vs-`error` pattern from this slice's log: any
    future per-action error state added to `DashboardView` (or a
    similarly-shaped component with an early-return `if (error) return`
    guard) should ask whether reusing that guard's state would blank the
    whole view before doing so. Not yet promoted to a standing rule
    (first occurrence) — but the next slice below hits this exact shape
    again (a re-run failure), so it's flagged explicitly in that brief's
    Constraints rather than left to be rediscovered.

## Next slice (the brief, written NOW while context is hot)

Goal:
Add a re-run button to each pinned card in `DashboardView.tsx` that calls
the already-shipped `POST /api/cards/{id}/run` and replaces that card's
`chart_spec_json`/`rows` with the fresh result on success.

Constraints:
- Frontend only (`web/src/api.ts` + `web/src/components/DashboardView.tsx`)
  — no backend changes; `POST /api/cards/{id}/run` already exists and is
  untouched.
- `web/src/api.ts` gains `runCard(id: number): Promise<DashboardCardWithRows>`
  following `fetchDashboard`'s existing throw-on-`!response.ok` /
  `return response.json()` shape (`api.ts` lines 62-68) — no request body.
- The button replaces just that one card's entry in `DashboardView`'s
  local `dashboard.cards` state (match by `id`, swap in the fresh
  `DashboardCardWithRows` the route returns), leaving every sibling card
  untouched — no full `fetchDashboard` refetch.
- On failure, leave the card's existing rows/chart unchanged and surface
  the error via a **new, dedicated re-run-error state** — explicitly NOT
  the page's initial-fetch `error` state, and NOT necessarily the same
  `deleteError` state either (reusing either risks the exact
  render-guard/parallel-error-state issue flagged in this handoff's Open
  questions — check `DashboardView.tsx`'s current render logic before
  choosing where the new state's error text renders).
- No new dependency, no per-card loading spinner/indicator during the
  re-run (out of scope — keep this slice to the request + swap only), no
  confirmation dialog.
- Match the existing file's style: functional component, `useState`,
  Tailwind utility classes consistent with the file's existing button
  (`text-sm text-red-600 hover:underline` for Delete — Re-run should read
  as visually distinct from Delete, e.g. a non-red accent, but stay
  within the file's existing minimal Tailwind vocabulary).

Inputs:
- `web/src/components/DashboardView.tsx` (current, post delete-slice) —
  the Delete button's `<div className="flex items-center justify-between">`
  wrapper is where a second button goes, alongside Delete.
- `web/src/api.ts`'s `fetchDashboard` (throw/parse shape) and `deleteCard`
  (fetch-with-method shape) as the two patterns to combine for `runCard`.
- `app/main.py`'s `run_dashboard_card` route (`app/main.py:440-459`): 200
  with a full `DashboardCardWithRows` body on success, 404
  `{"detail": "card not found"}` on an unknown id, 502 on SQL execution
  failure — the contract `runCard` calls against; no backend inspection
  beyond confirming this contract, since the route itself is out of scope.
- `web/tests/DashboardView.test.tsx` (existing, extend in place) and
  `web/tests/api.deleteCard.test.ts` (existing, as the pattern to mirror
  for a new `api.runCard.test.ts`).

Outputs:
- `web/src/api.ts` gains `runCard(id: number): Promise<DashboardCardWithRows>`.
- `web/src/components/DashboardView.tsx`'s per-card `<li>` gains a
  "Re-run" button; clicking it calls `runCard(card.id)` and replaces that
  card's `chart_spec_json`/`rows` with the fresh response on success, or
  leaves the card unchanged and shows an error on failure.
- Test coverage for: button present per card; successful re-run updates
  only that card's data (siblings' data untouched, confirmed by
  inspecting the card's own chart/rows-derived render, not just its
  title); failed re-run leaves the card's existing data unchanged and
  surfaces an error without blanking the rest of the list; no extra
  `fetchDashboard` call on either path.

Done-check:
`cd web && npm run build` (type-checks + builds cleanly) plus a real-server
shipping proof: create a real pinned card via curl, load the Dashboard tab
in a real browser (Playwright or manual), click its Re-run button, confirm
the request hits `POST /api/cards/{id}/run` and the rendered card updates
with the response (values may be identical if the underlying data hasn't
changed — the proof is that the round-trip happened and re-rendered, not
that the numbers changed), and confirm no console errors and no change to
sibling cards.

Out-of-scope:
- Rename input and drag-to-reposition — the other two remaining card
  actions; each is its own future slice.
- A confirmation dialog before re-running — re-running is a read-only,
  idempotent-from-the-user's-perspective action; not requested.
- A per-card loading spinner/indicator while the re-run request is in
  flight — a real UX gap, but a separate, smaller slice on top of this
  one rather than bundled in.
- Any backend change to `POST /api/cards/{id}/run` itself.
- The orphaned `plans/logs/2026-08-07-run-dashboard-card-endpoint.md`
  cleanup — unrelated file, separate housekeeping slice.
- Wiring up a frontend test runner (vitest/jest) — a new dependency,
  needs its own explicit ask per CLAUDE.md's standing rules.
