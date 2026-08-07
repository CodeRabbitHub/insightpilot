# Review gate — dashboard-card-rerun-button

Date: 2026-08-07
Brief: plans/briefs/2026-08-07-dashboard-card-rerun-button.md
Diff reviewed: working tree vs HEAD (685b7b1), pre-commit

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review
`git diff --stat`:
```
 web/src/api.ts                       |   8 ++
 web/src/components/DashboardView.tsx |  38 +++++--
 web/tests/DashboardView.test.tsx     | 214 ++++++++++++++++++++++++++++++++++-
 web/tests/api.deleteCard.test.ts     |  18 +--
 web/tests/api.fetchDashboard.test.ts |  18 +--
 6 files changed, 273 insertions(+), 42 deletions(-)
```
Plus new untracked: `web/tests/api.runCard.test.ts`, `web/tests/helpers/mockFetch.ts`,
`plans/briefs/2026-08-07-dashboard-card-rerun-button.md`. Fully read line by
line. PASS.

## 2. The stated goal matches the actual change
Brief's Goal: add a Re-run button to each pinned card calling the existing
`POST /api/cards/{id}/run`, replacing that card's `chart_spec_json`/`rows`
with the fresh result on success.

Diff does exactly this: `runCard(id)` added to `api.ts` mirroring
`fetchDashboard`'s throw/parse shape; `DashboardView.tsx` gains a dedicated
`rerunError` state, a `handleRerun` swapping the matching card by id via
`setDashboard`, and a "Re-run" button (blue, left of Delete) in the
per-card action row. No backend change, no confirmation dialog, no
spinner — all correctly out-of-scope per the brief. The only changes
beyond the literal Outputs list are two no-slop fixes surfaced during
review (below), not scope creep. PASS.

## 3. The eval or test passed
No LLM behavior touched -- no eval run needed. Done-check run fresh:
```
> web@0.0.0 build
> tsc -b && vite build

vite v8.2.0 building client environment for production...
✓ 628 modules transformed.
✓ built in 3.52s
```
New/extended test files (`api.runCard.test.ts`, `DashboardView.test.tsx`
re-run sections) written from the brief before the code existed, following
the `deleteCard`/delete-button precedent exactly. Still cannot execute —
no vitest/jsdom wired into `web/package.json` (standing gap, noted not
hidden, same as every prior frontend test file). PASS (build clean; test
execution gap is a pre-existing, disclosed limitation, not new to this
slice).

## 4. The no-slop review found no unresolved issues
Two passes via the no-slop-reviewer subagent.

Pass 1 findings:
- **Duplication**: `mockFetchOnce`/`vi.stubGlobal`/`afterEach(unstub)` block
  copy-pasted a third time in the new `api.runCard.test.ts` (already
  duplicated in `api.fetchDashboard.test.ts` and `api.deleteCard.test.ts`).
  Fixed: extracted to `web/tests/helpers/mockFetch.ts`; all three test
  files now import it.
- **Consistency**: new button wrapper used `gap-4`, inconsistent with the
  project's existing `gap-2` convention (`App.tsx`, `FollowUpChips.tsx`).
  Fixed: changed to `gap-2`.

Pass 2 (re-review of the fixed diff): confirmed both fixes landed
correctly (single `mockFetchOnce` definition, all three consumers import
it; `gap-2` in place). Found one further cosmetic issue: the new helper's
comment named its three current callers by file, which would go stale on
a fourth caller. Fixed: reworded to describe the guaranteed property
instead of enumerating callers.

Final rebuild after all three fixes: clean (`✓ built in 3.52s`). Zero
unresolved findings. PASS.

## 5. The shipping proof is attached
Real-server + real-browser proof, run twice (once before the no-slop
fixes, once after, against the final diff):
- `POST /api/dashboards/1/cards` created a real proof card (ids 2295,
  2296 across the two runs; a third independent run by the reviewer
  subagent used id 2297).
- Headless Chromium (Playwright, transient dependency, not added to
  `package.json`) opened the Dashboard tab on the running Vite dev
  server, located the proof card, clicked its real "Re-run" button.
- Confirmed via network trace: `POST http://localhost:8000/api/cards/{id}/run`
  → 200. Zero console errors. Sibling `<li>` headings identical before and
  after (8 total, unchanged). No extra `GET /api/dashboards/1` call after
  the click.
- Each proof card was deleted afterward via `DELETE /api/cards/{id}` → 204.
  Verified server-side: dashboard 1 still has exactly 7 cards, all
  pre-existing pollution from prior sessions (documented in HANDOFF.md),
  zero new pollution from this slice.
PASS.

## Rejected or changed
- Extracted third-copy `mockFetchOnce` test helper into
  `web/tests/helpers/mockFetch.ts` (no-slop pass 1).
- Changed `gap-4` to `gap-2` in the new button wrapper for consistency
  with the rest of the codebase (no-slop pass 1).
- Reworded the new helper's doc comment to avoid naming specific caller
  files, which would go stale (no-slop pass 2).
- Nothing was rejected outright; no proposed change was declined.

## Verdict
accept — all five checks green. User confirmed acceptance 2026-08-07.
