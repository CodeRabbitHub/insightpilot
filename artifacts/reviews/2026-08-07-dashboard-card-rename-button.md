# Review gate — dashboard-card-rename-button

Date: 2026-08-07
Brief: plans/briefs/2026-08-07-dashboard-card-rename-button.md
Diff reviewed: working tree vs HEAD (024473e), pre-commit

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review
`git diff --stat` (scoped to this slice's files -- `HANDOFF.md` and
`plans/logs/_auto-capture.md` also show modified but are pre-existing
dirty state from before this session, not part of this diff):
```
 web/src/api.ts                       |  17 +-
 web/src/components/DashboardView.tsx |  69 ++++++--
 web/tests/DashboardView.test.tsx     | 313 ++++++++++++++++++++++++++++++++++-
 3 files changed, 380 insertions(+), 19 deletions(-)
```
Plus new untracked: `web/tests/api.renameCard.test.ts` (116 lines),
`plans/briefs/2026-08-07-dashboard-card-rename-button.md`. Fully read
line by line. PASS.

## 2. The stated goal matches the actual change
Brief's Goal: add a rename control to each pinned card calling the
existing `PATCH /api/cards/{id}` (title-only), updating that card's title
in place on success.

Diff does exactly this: `renameCard(id, title)` + `DashboardCardDetail`
added to `api.ts`; `DashboardView.tsx` gains a "Rename" button
(`text-gray-700`, between Re-run and Delete) wired to `handleRename`,
which prompts via `window.prompt`, no-ops on cancel/empty/whitespace, and
on success merges only `title` into the matching card (never swapping the
whole object, since the PATCH response has no `rows`). No backend change,
no custom modal — both correctly out-of-scope per the brief.

**Flagged deviation, decided by user:** the no-slop review's pass 1 found
the brief's literal Constraints text (a fourth dedicated `renameError`
state, distinct from `error`/`deleteError`/`rerunError`) would create a
third occurrence of an identical error-state/handler/button shape across
delete/rerun/rename. Consolidated all three into one shared `actionError`
state + a shared `updateCard(cardId, merge)` helper instead, per this
project's own precedent (the rerun slice's `mockFetchOnce` extraction) of
fixing third-occurrence duplication inline rather than deferring it.
Presented to the user as an explicit choice; user chose to keep the
consolidation over brief-literal compliance. PASS (goal met; the one
deviation was surfaced, not smuggled in, and decided by the user).

## 3. The eval or test passed
No LLM behavior touched — no eval run needed. Done-check run fresh, after
all no-slop fixes:
```
> web@0.0.0 build
> tsc -b && vite build

vite v8.2.0 building client environment for production...
✓ 628 modules transformed.
✓ built in 2.26s
```
New `api.renameCard.test.ts` and extended `DashboardView.test.tsx`
written from the brief before the code existed (test-writer subagent),
covering: button presence, prompt default value, cancel/empty/whitespace
no-op, successful rename (title-only merge, rows/chart_spec_json
preserved via `ChartView` spy, sibling isolation), failed rename (title
unchanged, error surfaced, siblings untouched), no extra `fetchDashboard`
call on any path. Still cannot execute — no vitest/jsdom wired into
`web/package.json` (standing gap, disclosed in both files' header
comments, not new to this slice). PASS (build clean; test-execution gap
is pre-existing and disclosed, not new).

## 4. The no-slop review found no unresolved issues
Two passes via the no-slop-reviewer subagent.

Pass 1 findings:
- **Duplication**: `DashboardCardDetail`/`DashboardCardWithRows` in
  `api.ts` hand-duplicated 7 of 8 fields instead of mirroring the
  backend's own inheritance (`app/main.py`'s
  `DashboardCardWithRows(DashboardCardDetail)`). Fixed: frontend
  `DashboardCardWithRows` now `extends DashboardCardDetail`.
- **Duplication (3rd occurrence)**: `deleteError`/`rerunError`/
  `renameError` states and their near-identical handler bodies. Fixed:
  consolidated into `actionError` + `updateCard` helper (see Check 2's
  flagged deviation above).
- Verified-not-claimed and HANDOFF.md-staleness notes were procedural
  (addressed by this gate itself / the standing handoff step), not code
  fixes.

Pass 2 (re-review of the fixed diff): confirmed both fixes landed
correctly. Found two cosmetic nits: a comment in `DashboardView.test.tsx`
still named the old `deleteError` state; a test description still said
"surfaces a renameError message." Fixed: both reworded to `actionError`.
Flagged the residual identical one-line `.catch((e) =>
setActionError(errorMessage(e)))` across all three handlers as a judged,
documented exception — further extraction (a generic `runAction`
wrapper) would be over-abstraction for one line, per CLAUDE.md's
no-premature-abstraction rule.

Final rebuild after all fixes: clean (`✓ built in 2.26s`). Zero
unresolved findings. PASS.

## 5. The shipping proof is attached
Real-server + real-browser proof, run against the final diff (after all
no-slop fixes):
- `POST /api/dashboards/1/cards` created a real proof card (id 2298,
  then recreated as 2299 after 2298's placeholder SQL referenced
  nonexistent tables and had to be deleted/recreated with valid SQL).
- Headless Chromium (Playwright, transient dependency installed in the
  scratchpad only, not added to `web/package.json`) opened the Dashboard
  tab on the running Vite dev server, located card 2299, clicked its real
  "Rename" button, and auto-accepted the native `window.prompt` dialog
  via Playwright's `page.on('dialog')`.
- Confirmed via network trace:
  ```json
  {
    "requests": [{"method":"PATCH","url":"http://localhost:8000/api/cards/2299",
                  "postData":"{\"title\":\"Renamed by Playwright proof v2\"}","status":200}],
    "consoleErrors": [],
    "headingsBeforeCount": 8, "headingsAfterCount": 8,
    "canvasCount": 1, "hasErrorText": false
  }
  ```
  Title updated in the DOM; chart canvas still rendered (rows/chart_spec
  not blanked); all 8 sibling headings identical before/after; zero
  console errors; no error text shown.
- Proof card deleted afterward (`DELETE /api/cards/2299` → 204). Verified
  server-side: dashboard 1 back to exactly 7 cards, all pre-existing
  pollution from prior sessions, zero new pollution from this slice.
PASS.

## Rejected or changed
- Made frontend `DashboardCardWithRows` extend `DashboardCardDetail`
  instead of hand-duplicating fields (no-slop pass 1).
- Consolidated `deleteError`/`rerunError`/`renameError` into one shared
  `actionError` state + extracted `updateCard` helper, deviating from the
  brief's literal Constraints wording — surfaced to the user as an
  explicit choice; user chose to keep it (no-slop pass 1, Check 2).
- Reworded a stale comment and a stale test description that still named
  the removed `deleteError`/`renameError` states (no-slop pass 2).
- Nothing was rejected outright; the one real judgment call (the state
  consolidation) was decided by the user, not unilaterally.

## Verdict
accept — all five checks green. User confirmed acceptance 2026-08-08.
