# Brief — dashboard-card-rerun-button

Date: 2026-08-07
Milestone: M6 Dashboard (card actions)

Goal:
Add a re-run button to each pinned card in `DashboardView.tsx` that calls
the already-shipped `POST /api/cards/{id}/run` and replaces that card's
`chart_spec_json`/`rows` with the fresh result on success.

Constraints:
- Frontend only (`web/src/api.ts` + `web/src/components/DashboardView.tsx`)
  — no backend changes; `POST /api/cards/{id}/run` already exists and is
  untouched.
- No new dependency (per ARCHITECT.md's excluded-deps list) — no router
  change, no confirmation dialog (re-running is read-only/idempotent from
  the user's perspective, so not requested).
- `web/src/api.ts` gains `runCard(id: number): Promise<DashboardCardWithRows>`
  following `fetchDashboard`'s existing throw-on-`!response.ok` /
  `return response.json()` shape (`api.ts` lines 62-68): `fetch` with
  `method: 'POST'` against `/api/cards/${id}/run`, no request body, throws
  `Error` with the route + status on failure, resolves with the parsed
  `DashboardCardWithRows` body on success.
- The button replaces just that one card's entry in `DashboardView`'s
  local `dashboard.cards` state (match by `id`, swap in the fresh
  `DashboardCardWithRows` the route returns via `setDashboard`), leaving
  every sibling card untouched — no full `fetchDashboard` refetch.
- On failure, leave the card's existing rows/chart unchanged and surface
  the error via a **new, dedicated re-run-error state** — explicitly NOT
  the page's initial-fetch `error` state (its `if (error) return <p>...</p>`
  guard at `DashboardView.tsx:35` would blank the whole card list), and NOT
  necessarily the same `deleteError` state either — check the current
  render logic before choosing where the new state's error text renders,
  same shape as the `deleteError`-vs-`error` split this file already
  carries a comment about (lines 9-11).
- No per-card loading spinner/indicator during the re-run (out of scope —
  keep this slice to the request + swap only).
- Match the existing file's style: functional component, `useState`,
  Tailwind utility classes consistent with the file's existing Delete
  button (`text-sm text-red-600 hover:underline`) — Re-run should read as
  visually distinct from Delete (e.g. a non-red accent), staying within
  the file's existing minimal Tailwind vocabulary.

Inputs:
- `web/src/components/DashboardView.tsx` (current, 62 lines, post
  delete-slice) — the per-card `<div className="flex items-center
  justify-between">` wrapper at lines 47-55 is where a second button goes,
  alongside Delete.
- `web/src/api.ts`'s `fetchDashboard` (lines 62-68, throw/parse shape) and
  `deleteCard` (lines 70-75, fetch-with-method shape) as the two patterns
  to combine for `runCard`.
- `app/main.py`'s `run_dashboard_card` route (`app/main.py:440-459`): 200
  with a full `DashboardCardWithRows` body on success, 404
  `{"detail": "card not found"}` on an unknown id, 502 on SQL execution
  failure — the contract `runCard` calls against; no backend inspection
  beyond confirming this contract, since the route itself is out of scope.
- `web/tests/DashboardView.test.tsx` (existing, extend in place) and
  `web/tests/api.deleteCard.test.ts` (existing, as the pattern to mirror
  for a new `web/tests/api.runCard.test.ts`).

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
  `fetchDashboard` call on either path. (Same standing gap as every prior
  frontend test file: no vitest/jest wired into `web/package.json` yet,
  so these cannot execute this session — noted rather than hidden.)

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
- A confirmation dialog before re-running — not requested.
- A per-card loading spinner/indicator while the re-run request is in
  flight — a real UX gap, but a separate, smaller slice on top of this
  one rather than bundled in.
- Any backend change to `POST /api/cards/{id}/run` itself.
- The orphaned `plans/logs/2026-08-07-run-dashboard-card-endpoint.md`
  cleanup — unrelated file, separate housekeeping slice.
- Wiring up a frontend test runner (vitest/jest) — a new dependency,
  needs its own explicit ask per CLAUDE.md's standing rules.
