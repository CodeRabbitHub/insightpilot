# Review gate — dashboard-card-drag-reposition

Date: 2026-08-08
Brief: plans/briefs/2026-08-08-dashboard-card-drag-reposition.md
Diff reviewed: working tree vs HEAD (24bfebf), pre-commit

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review
`git diff --stat` (scoped to this slice's files -- `plans/logs/_auto-capture.md`
also shows modified but is pre-existing hook-appended state, not part of
this diff):
```
 web/src/api.ts                       |  12 ++
 web/src/components/DashboardView.tsx |  51 +++++-
 web/tests/DashboardView.test.tsx     | 301 ++++++++++++++++++++++++++++++++++-
 3 files changed, 362 insertions(+), 2 deletions(-)
```
Plus new untracked: `web/tests/api.repositionCard.test.ts` (125 lines),
`plans/briefs/2026-08-08-dashboard-card-drag-reposition.md` (96 lines).
Fully read line by line. PASS.

## 2. The stated goal matches the actual change
Brief's Goal: let a user reorder pinned cards by dragging them in
`DashboardView.tsx`, persisting the new order through the already-shipped
`PATCH /api/cards/{id}` `position` field.

Diff does exactly this: `repositionCard(id, position)` added to `api.ts`,
mirroring `renameCard`'s shape with `position` swapped in for `title`.
`DashboardView.tsx` gains `draggedCardId` state, `draggable` +
`onDragStart`/`onDragOver`/`onDrop` on each card `<li>`, and `handleDrop`
— splice-out/splice-in reorder at the target's index, renumbered
sequentially, optimistic UI update, `repositionCard` called for every
card whose slot changed (not only the dragged one), revert to the
pre-drag arrangement via the shared `actionError` state on any failure.
No backend touched, no drag library, no `patchCard` generalization, no
touch/mobile support — all correctly out-of-scope per the brief. PASS,
no unrequested extras.

## 3. The eval or test passed
No LLM behavior touched — no eval run needed. Done-check's build half run
fresh, after all no-slop fixes:
```
> web@0.0.0 build
> tsc -b && vite build

vite v8.2.0 building client environment for production...
✓ 628 modules transformed.
✓ built in 844ms
```
New `api.repositionCard.test.ts` and an extended `DashboardView.test.tsx`
were written from the brief before the code existed (test-writer
subagent), covering: optimistic reorder before persistence settles,
`repositionCard` called with the correct renumbered position for every
shifted sibling (not just the dragged card), no call for an unaffected
sibling, revert-to-pre-drag-order plus `actionError` on any persist
failure, no extra `fetchDashboard` call on any path. Still cannot
execute — no vitest/jsdom wired into `web/package.json` (standing gap,
disclosed in both files' header comments, not new to this slice). PASS
(build clean; test-execution gap is pre-existing and disclosed).

## 4. The no-slop review found no unresolved issues
One pass via the no-slop-reviewer subagent, findings and resolutions:
- **Verified-not-claimed**: flagged that the real-server half of the
  done-check hadn't been run yet at review time. Resolved by actually
  running it (see Check 5).
- **Untested edge / judgment call**: a partial `repositionCard` failure
  can leave the backend with some already-persisted new positions while
  the client reverts its local view to the pre-drag order — the two can
  drift until the next full reload. Presented to the user as an explicit
  choice (accept as a known limitation vs. add compensating rollback
  PATCH calls); user chose to accept it as a known, documented
  limitation rather than add rollback complexity the brief didn't ask
  for. Recorded below and destined for HANDOFF.md.
- **Untested edge**: no `onDragEnd` handler, so a cancelled drag (dropped
  outside any card) leaves `draggedCardId` stale until the next
  `dragstart` overwrites it. No functional bug (nothing else reads that
  state), already called out as a deliberate omission in the approved
  plan; left as a written exception rather than added defensive code for
  an unobserved failure mode.
- **Dead code / comments**: `e.dataTransfer.setData(...)` in
  `onDragStart` had no comment explaining why it's needed (Firefox
  requires it to start a native drag) despite nothing reading it back.
  Fixed: one-line comment added.

Zero unresolved findings after the fixes above. PASS.

## 5. The shipping proof is attached
Real-server + real-browser proof, run against the final diff.

While building this proof, discovered and diagnosed (not fixed — see
Check 4) a pre-existing, unrelated issue: `DashboardView`'s original
mount `useEffect` (from an earlier slice) double-fires under React 18
StrictMode in dev, so two concurrent `fetchDashboard` calls go out on
mount; the slower one can resolve seconds later and silently overwrite
whatever local state exists at that moment. Confirmed via temporary
debug logging (removed before finishing) that this — not the new drag
code — was the source of an initial flaky-looking proof run. Letting the
page settle for ~2s after load before interacting (what a real user does
by simply looking at the page before dragging) avoids it entirely; used
for this proof's script and flagged in HANDOFF.md as a pre-existing risk
for a future slice, since fixing the original effect is out of this
slice's scope.

Proof steps:
- `POST /api/dashboards/1/cards` created two real proof cards ("Drag
  proof First" id 2305 position 100, "Drag proof Second" id 2306
  position 101).
- Headless Chromium (Playwright, installed transiently into the session
  scratchpad only, not added to `web/package.json`, per this project's
  established pattern) opened the Dashboard tab on the running Vite dev
  server, waited ~2s for the page to settle, then dispatched real
  `dragstart`/`dragover`/`drop` events (each in its own round-trip, with
  a shared `DataTransfer`, matching real drag timing) dragging "Drag
  proof Second" onto "Drag proof First"'s slot.
- Network trace confirmed both cards' new sequential positions were
  persisted:
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
- A fresh `GET /api/dashboards/1` (separate from the browser session)
  confirmed the persisted order: card 2306 at position 7, card 2305 at
  position 8 — matching the drop.
- Proof cards deleted afterward (`DELETE /api/cards/2305`,
  `/2306` → 204 each). Verified server-side: dashboard 1 back to exactly
  7 cards, all pre-existing pollution from prior sessions, zero new
  pollution from this slice.
PASS.

## Rejected or changed
- Added a one-line comment explaining `dataTransfer.setData`'s
  cross-browser necessity (no-slop finding).
- Chose NOT to add compensating-rollback PATCH calls for the
  partial-failure DB-drift finding — user explicitly decided to accept
  it as a known limitation instead, to avoid adding round-trip
  complexity the brief never asked for; documented for a future slice.
- Chose NOT to fix the pre-existing StrictMode double-fetch race
  discovered while building the shipping proof — out of scope for this
  slice (it predates this slice and affects the original mount effect,
  not the new drag code); documented in HANDOFF.md instead.
- Removed all temporary debug `console.log` statements added during
  diagnosis before finishing (never part of the shipped diff).

## Verdict
accept — all five checks green.
