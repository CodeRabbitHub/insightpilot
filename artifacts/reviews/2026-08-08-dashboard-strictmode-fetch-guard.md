# Review gate — dashboard-strictmode-fetch-guard

Date: 2026-08-08
Brief: plans/briefs/2026-08-08-dashboard-strictmode-fetch-guard.md
Diff reviewed: working tree — `web/src/components/DashboardView.tsx`,
`web/tests/DashboardView.test.tsx` (uncommitted at review time)

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review

```
 web/src/components/DashboardView.tsx |  16 ++-
 web/tests/DashboardView.test.tsx     | 186 +++++++++++++++++++++++++++++++++++
 2 files changed, 199 insertions(+), 3 deletions(-)
```
Source change is a 13-line effect body; test additions are new `describe`
blocks plus a small `deferred()` helper. Fully reviewable line by line.

## 2. The stated goal matches the actual change

Brief's Goal: fix `DashboardView.tsx`'s mount effect so StrictMode's
dev-only double-invoke can never let a stale duplicate `fetchDashboard`
response overwrite newer state.

Diff: adds a local `stale` flag to the mount effect, checked before each
of `setDashboard`/`setError`/`setLoading` in `.then`/`.catch`/`.finally`,
flipped `true` in the effect's cleanup. No other handler, state, or drag
logic touched. Matches exactly — no extra scope.

## 3. The eval or test passed

```
$ cd web && npm run build
> web@0.0.0 build
> tsc -b && vite build

vite v8.2.0 building client environment for production...
✓ 628 modules transformed.
✓ built in 856ms
```

Real-server shipping proof doubles as the done-check's second clause (see
§5) — reproduced the bug live on pre-fix code, then confirmed the fix
holds on final code. New unit tests written (`web/tests/DashboardView.test.tsx`)
but not executable — same standing repo-wide gap, no vitest/jsdom wired
into `web/package.json` yet.

## 4. The no-slop review found no unresolved issues

Two passes, both via the `no-slop-reviewer` subagent.

**Pass 1 findings, all fixed:**
- Flag named `ignore` (per brief's literal Constraints text) while the
  identical pre-existing guard pattern in `web/src/App.tsx:173-194` names
  it `stale` — inconsistent vocabulary for the same concept in the same
  codebase. Fixed: renamed to `stale` in both the component and the
  test file's comments.
- An incidental, unrelated reword of a pre-existing comment (about the
  Rename button's card-merge semantics) had been smuggled into the test
  file by the test-writer agent. Fixed: reverted to original wording,
  confirmed byte-for-byte against commit `1cc5574`.
- The new race tests only proved the `.then`/`.catch` guards; the
  `setLoading` guard specifically was unproven (both tests only exercised
  the ordering where the stale call settles *after* the fresh one, where
  an unguarded `finally` would be visually indistinguishable). Fixed:
  added a third test resolving the stale call *before* the fresh one,
  while the fresh call is still pending, asserting loading stays visible
  and stale data doesn't render.
- (Noted, not a defect: `App.tsx`'s *other* effect, the conversations-list
  fetch at lines ~164-171, has the identical unguarded race. Out of scope
  per this brief; carried to HANDOFF.md as a discovered-but-deferred item
  for a future slice.)

**Pass 2 finding, fixed:**
- A test-file header comment narrated the session's TDD sequencing
  ("written BEFORE the fix lands... expected to fail against the current
  pre-fix effect body") rather than describing current behavior — stale
  on arrival once merged. Fixed: reworded to present tense, matching the
  style of the later per-`describe`-block comments.

**Pass 2 clean** on all remaining checklist categories (dead code,
unhandled errors, duplication, naming after fix, untested edges, project
consistency, scope, fake-done markers).

## 5. The shipping proof is attached

Real dev servers (API :8000, web :5173, both already running from a prior
session). Playwright (scratchpad-installed per this project's established
pattern) dispatched real `dragstart`/`dragover`/`drop` events.

**Pre-fix repro** (code temporarily reverted via `git stash` to confirm
the bug is real before trusting the fix):
```json
{
  "headingsBeforeDrag": ["Race proof First", "Race proof Second"],
  "headingsRightAfterDrop": ["Race proof Second", "Race proof First"],
  "headingsAfter6sWait": ["Race proof First", "Race proof Second"],
  "consoleErrors": []
}
```
Reorder visibly reverts after ~6s — the exact race the brief describes.

**Post-fix confirmation** (final code, fresh proof cards, after the
no-slop fixes above):
```json
{
  "headingsBeforeDrag": ["Race proof First", "Race proof Second"],
  "headingsRightAfterDrop": ["Race proof Second", "Race proof First"],
  "headingsAfter6sWait": ["Race proof Second", "Race proof First"],
  "consoleErrors": []
}
```
Reorder survives the full 6-second wait — no revert, zero console errors
on either run. Proof cards (ids 2305-2310 across both proof rounds)
deleted afterward; dashboard 1 reconfirmed back to its baseline 7
pre-existing cards each time.

## Rejected or changed

- Flag renamed `ignore` → `stale`, deviating from the brief's literal
  Constraints text (which specified `ignore`, citing React's own docs) —
  judgment call, presented to and accepted by the user: cross-file
  vocabulary consistency with `App.tsx`'s identical existing pattern
  outweighs matching the external doc's literal naming.
- Incidental unrelated comment reword in the test file — rejected/reverted,
  out of this slice's scope.
- Test coverage gap on the `setLoading` guard — changed: added a third
  race test to close it.
- Stale TDD-process comment in the test file — changed: reworded to
  present tense.

## Verdict

**accept** — all five checks green; the one judgment call (naming
deviation) presented to and accepted by the user.
