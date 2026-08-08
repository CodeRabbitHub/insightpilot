# Review gate — app-strictmode-fetch-guard

Date: 2026-08-08
Brief: plans/briefs/2026-08-08-app-strictmode-fetch-guard.md
Diff reviewed: working tree vs HEAD (2565d38) — web/src/App.tsx,
web/tests/App.test.tsx (new), plans/briefs/2026-08-08-app-strictmode-fetch-guard.md (new)

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review

```
 plans/briefs/2026-08-08-app-strictmode-fetch-guard.md | 111 ++++++++++
 web/src/App.tsx                                       |  16 +-
 web/tests/App.test.tsx                                | 245 +++++++++++++++++++++
 3 files changed, 369 insertions(+), 3 deletions(-)
```
One production file changed (+16/-3), one new test file, one new brief.
Fully readable line by line. PASS.

## 2. The stated goal matches the actual change

Brief's Goal: fix `App.tsx`'s conversations-list mount effect so React 18
StrictMode's dev-only double-invoke can never let a stale duplicate
`fetchConversations` response overwrite newer state.

The diff adds a local `stale` boolean (`false` at the top of the effect),
guards `setConversations`/`setError`/`setLoading` in
`.then`/`.catch`/`.finally` behind `if (!stale)`, and flips `stale = true`
in the effect's returned cleanup — the exact shape of this same file's
already-correct conversation-detail effect (lines 173-194) and
`DashboardView.tsx`'s previously-fixed mount effect. Nothing else in
`App.tsx` changed. Matches; no unrequested extras. PASS.

## 3. The eval or test passed

Done-check run fresh:
```
> web@0.0.0 build
> tsc -b && vite build

vite v8.2.0 building client environment for production...
✓ 628 modules transformed.
✓ built in 965ms
```
Frontend unit tests (`web/tests/App.test.tsx`, new this slice) still
cannot execute — no vitest/jsdom wired into `web/package.json` (standing,
repo-wide gap predating this slice, same as every other frontend test
file). Written from the brief by the test-writer subagent, reviewed for
correctness in lieu of execution. PASS (build half); test-execution gap
disclosed, not hidden.

## 4. The no-slop review found no unresolved issues

Two passes via the no-slop-reviewer subagent.

**Pass 1** findings (both fixed before pass 2):
- Category 6 (Comments): `web/tests/App.test.tsx`'s header carried a
  stale TDD-narration comment ("Written from the brief alone, before
  App.tsx's mount effect has the stale-flag guard added") that was
  already false by the time the diff lands the guard in the same commit
  — the identical defect the immediately-prior slice's own review caught
  and fixed on the sibling `DashboardView.test.tsx`. Fixed: reworded to
  drop the temporal claim.
- Minor (Category 1, non-blocking): `fetchConversation`/
  `postConversationMessage` mocked in the module factory but never
  exercised by any test (every test keeps `selectedId === null`). Fixed:
  one-line justification comment added explaining why they're stubbed
  anyway (so the whole `../src/api` module resolves without a real
  network call).
- Noted, not a finding: `deferred()` is now a 2nd occurrence (duplicate of
  `DashboardView.test.tsx`'s own helper) — per the ratchet's 3rd-occurrence
  rule, extraction isn't warranted yet.

**Pass 2** (fresh, against the final diff): confirmed both fixes landed
cleanly and introduced nothing new; full 10-category walk otherwise clean.

Zero unresolved findings at gate time. PASS.

## 5. The shipping proof is attached

Real dev servers reused from prior sessions (`vite` on :5173, `uvicorn` on
:8000 — both confirmed up via `curl` before starting). Playwright
(scratchpad-installed `pw-drag/`, reused across sessions per established
pattern) with route interception on `GET /api/conversations`: the first
(StrictMode's stale first invocation) response is delayed 2.5s and
returns a `STALE PROOF MARKER` conversation; the second (fresh) response
returns a `FRESH PROOF MARKER` conversation immediately, no delay.

**Fixed code:**
```json
{
  "callCount": 2,
  "freshMarkerShownEarly": true,
  "staleMarkerShownEarly": false,
  "freshMarkerAfterWait": true,
  "staleMarkerAfterWait": false,
  "consoleErrors": []
}
```
Two real requests fired (StrictMode's double-invoke genuinely happened),
fresh marker shows and survives the stale call's late resolution, zero
console errors.

**Pre-fix repro** (`git stash push -- web/src/App.tsx`, confirmed via
`git diff` that only the guard was reverted, Vite HMR picked it up):
```json
{
  "callCount": 2,
  "freshMarkerShownEarly": true,
  "staleMarkerShownEarly": false,
  "freshMarkerAfterWait": false,
  "staleMarkerAfterWait": true,
  "consoleErrors": []
}
```
Fresh marker shows initially, then gets clobbered by the late-resolving
stale call — bug reproduced for real, not assumed.

**Post-restore re-confirmation** (`git stash pop`, re-ran the same
script): identical to the "Fixed code" result above — fix reproduced
again after restoring it. PASS.

## Rejected or changed

The test-writer subagent's first draft of `web/tests/App.test.tsx` carried
a stale TDD-narration header comment (recurrence of a defect the prior
slice's own review had already caught on a sibling file) and an
unexplained defensive mock — both caught by no-slop pass 1 and fixed
before pass 2. Nothing in the implementation itself (App.tsx's guard) was
rejected or changed from the approved plan.

## Verdict

**accept** — all five checks green.
