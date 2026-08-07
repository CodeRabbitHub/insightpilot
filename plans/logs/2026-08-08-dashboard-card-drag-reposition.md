# Slice log — dashboard-card-drag-reposition

Date: 2026-08-08
Brief: plans/briefs/2026-08-08-dashboard-card-drag-reposition.md

## The plan you approved
Add `repositionCard(id, position)` to `api.ts`, mirroring `renameCard`'s
PATCH+JSON shape exactly. Wire native HTML5 drag-and-drop (`draggable` +
`onDragStart`/`onDragOver`/`onDrop`) onto each card `<li>`; on drop,
splice the dragged card into the target's slot, renumber sequentially,
apply the reorder optimistically, then PATCH every card whose position
actually changed (not just the dragged one). Revert to the pre-drag
arrangement via the existing shared `actionError` state on any failure.

## The diff you accepted
Commit `1cc5574` — "Add drag-to-reposition for pinned dashboard cards".
6 files changed, 736 insertions(+), 2 deletions(-): `web/src/api.ts`
(+12), `web/src/components/DashboardView.tsx` (+51), extended
`web/tests/DashboardView.test.tsx` (+301), new
`web/tests/api.repositionCard.test.ts` (125 lines), plus this slice's
brief and gate review. Full mechanics in
`plans/logs/_auto-capture.md`.

## The done-check output
```
> web@0.0.0 build
> tsc -b && vite build

vite v8.2.0 building client environment for production...
✓ 628 modules transformed.
✓ built in 844ms
```
Real-server shipping proof (final diff): two proof cards created via
`POST /api/dashboards/1/cards` (ids 2305/2306, positions 100/101);
headless Chromium (Playwright, scratchpad-installed) dispatched real
`dragstart`/`dragover`/`drop` events dragging "Drag proof Second" onto
"Drag proof First"'s slot:
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
A fresh `GET /api/dashboards/1` confirmed the persisted order (2306 at
position 7, 2305 at position 8). Proof cards deleted afterward; dashboard
1 back to exactly 7 pre-existing cards, zero new pollution.

## One thing you rejected or changed
The no-slop reviewer flagged that a partial `repositionCard` failure can
leave the backend with some already-persisted new positions while the
client reverts its local view to the pre-drag order — the two drift
until the next full reload. Presented as an explicit choice
(accept-as-known-limitation vs. add compensating rollback PATCH calls
for the succeeded writes); chose to accept it as a documented known
limitation rather than add round-trip rollback complexity the brief
never asked for. First occurrence of this specific tradeoff in the
project — not yet a promotion candidate, but worth watching if a similar
call comes up again.

## The next smallest slice
Fix the pre-existing React StrictMode double-fetch race discovered while
building this slice's shipping proof: `DashboardView`'s mount `useEffect`
fires twice in dev (StrictMode), sending two concurrent `fetchDashboard`
calls, and the slower one can resolve seconds later and silently
overwrite whatever local state exists at that moment (a completed drag
reorder, an in-progress rename, etc.) — likely fixable with an
`AbortController` or a mount-ref ignore-stale-response guard in that one
effect.
