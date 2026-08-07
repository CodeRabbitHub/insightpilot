# Brief — dashboard-card-drag-reposition

Date: 2026-08-08
Milestone: M6 Dashboard (card actions)

Goal:
Let a user reorder pinned cards by dragging them in `DashboardView.tsx`,
persisting the new order through the already-shipped
`PATCH /api/cards/{id}` (`position` field).

Constraints:
- Frontend only (`web/src/api.ts` + `web/src/components/DashboardView.tsx`)
  — no backend changes; `PATCH /api/cards/{id}` and `get_dashboard`'s
  `ORDER BY DashboardCard.position` (`app/main.py:380`) already exist and
  are untouched.
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
  consolidation the prior slice shipped) — on any `repositionCard`
  failure, revert the local reorder rather than leaving the UI showing an
  order that didn't actually persist.
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
dispatching `dragstart`/`dragover`/`drop` events — remember the prior
session's scratchpad-install workaround for resolving the `playwright`
package, or manual), drag one card to a new slot, confirm
`PATCH /api/cards/{id}` requests fire with the correct new `position`
values, confirm a fresh `GET /api/dashboards/1` reflects the new order,
and confirm no console errors. Delete proof cards afterward.

Out-of-scope:
- Any backend change to `PATCH /api/cards/{id}` or `get_dashboard`'s sort.
- Touch-screen/mobile drag support — the native HTML5 drag-and-drop API
  is desktop-mouse-only; a known limitation, not fixed here.
- Generalizing `renameCard`/`repositionCard` into one shared `patchCard`
  function — explicitly deferred per this brief's Constraints until a
  third PATCH variant exists.
- Adding a secondary sort key to `get_dashboard`'s `ORDER BY` even if the
  all-zero `position` tie observed in a prior session turns out to
  matter — flag it if it does, fix it in its own slice, don't fold it
  into this one.
- The orphaned `plans/logs/2026-08-07-run-dashboard-card-endpoint.md`
  cleanup — unrelated file, separate housekeeping slice.
- Wiring up a frontend test runner (vitest/jest) — a new dependency,
  needs its own explicit ask per CLAUDE.md's standing rules.
