# Brief — dashboard-card-delete-button

Date: 2026-08-07
Milestone: M6 Dashboard (card actions)

Goal:
Add a delete button to each pinned card in `DashboardView.tsx` that calls
the already-shipped `DELETE /api/cards/{id}` and removes that card from
the rendered list on success.

Constraints:
- Frontend only (`web/src/api.ts` + `web/src/components/DashboardView.tsx`)
  — no backend changes; `DELETE /api/cards/{id}` already exists and is
  untouched.
- No new dependency (per ARCHITECT.md's excluded-deps list) — no router
  change, no confirmation dialog/modal (out of scope).
- `web/src/api.ts` gains a `deleteCard(id: number): Promise<void>`
  function following `fetchDashboard`'s existing throw-on-`!response.ok`
  shape (`api.ts` lines 62-68) — `fetch` with `method: 'DELETE'`, no
  request body, throws `Error` with the route + status on failure,
  resolves with nothing (`void`) on the real 204 empty-body success case
  (do not attempt to parse a JSON body from a 204 response).
- The button removes the card from `DashboardView`'s local `dashboard`
  state optimistically-on-success only: call `deleteCard`, and on success
  filter the deleted id out of `dashboard.cards` via `setDashboard`; on
  failure, leave the card in place and surface the error via the existing
  `error` state / `errorMessage(e)` helper, not a silent no-op. No full
  `fetchDashboard` refetch needed for this action.
- Match the existing file's style: functional component, `useState`,
  Tailwind utility classes consistent with the existing `<h3>`/`<p>`
  classes in this file.

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
  place for the new button.

Outputs:
- `web/src/api.ts` gains `deleteCard(id: number): Promise<void>`.
- `web/src/components/DashboardView.tsx`'s per-card `<li>` gains a
  "Delete" button; clicking it calls `deleteCard(card.id)` and removes
  that card from the rendered list on success, or shows an error and
  leaves the card in place on failure.
- Test coverage added to `web/tests/DashboardView.test.tsx` for: button
  present per card, successful delete removes only that card from the
  list (siblings untouched), failed delete leaves the card in place and
  surfaces an error. (Cannot execute this session — no vitest/jest wired
  into `web/package.json` yet; note explicitly rather than claiming a
  pass, same known limitation as every prior frontend test file.)

Done-check:
`cd web && npm run build` (type-checks + builds cleanly) plus a real-server
shipping proof: create a real pinned card via `curl`, load the Dashboard
tab in a real browser (Playwright or manual), click its Delete button,
confirm it disappears from the rendered page, and confirm via a fresh
`GET /api/dashboards/{id}` curl that the row is genuinely gone
server-side — not just removed from the DOM.

Out-of-scope:
- Rename input, re-run button, and drag-to-reposition — the other three
  card actions flagged as missing UI; each is its own future slice.
- A confirmation dialog/modal before deleting — not requested, and this
  brief's Goal is the single action, not a UX safety net around it.
- Any backend change to `DELETE /api/cards/{id}` itself.
- The orphaned `plans/logs/2026-08-07-run-dashboard-card-endpoint.md`
  cleanup — unrelated file, separate housekeeping slice.
- Wiring up a frontend test runner (vitest/jest) — a new dependency,
  needs its own explicit ask per CLAUDE.md's standing rules.
