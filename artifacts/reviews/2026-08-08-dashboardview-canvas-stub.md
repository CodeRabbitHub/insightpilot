# Review gate — dashboardview-canvas-stub

Date: 2026-08-08
Brief: plans/briefs/2026-08-08-dashboardview-canvas-stub.md
Diff reviewed: working tree diff, `web/tests/setup.ts` + `web/tests/DashboardView.test.tsx` (uncommitted at gate time)

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review
```
 web/tests/DashboardView.test.tsx |  44 ++++++++++++-----
 web/tests/setup.ts               | 100 +++++++++++++++++++++++++++++++++++++++
 2 files changed, 132 insertions(+), 12 deletions(-)
```
Two files, both under `web/tests/`, fully read line by line. PASS.

## 2. The stated goal matches the actual change
Brief's Goal: get `web/tests/DashboardView.test.tsx` passing for real by resolving its
jsdom canvas/echarts crashes, without weakening its real-`<canvas>`-DOM-node proof of
per-card chart invocation.

What the diff does:
- `web/tests/setup.ts`: adds (a) a `HTMLCanvasElement.prototype.getContext('2d')` stub
  (the anticipated fix) and (b) a `globalThis.requestAnimationFrame` patch that resolves
  via `queueMicrotask` instead of jsdom's real ~16ms timer. (b) was not anticipated in
  the brief, but investigation during BUILD showed the canvas-context crash was
  necessary-but-not-sufficient: canvas creation itself is gated behind zrender's
  real-timer-driven animation loop (zrender captures `window.requestAnimationFrame`
  once at module load and drives its whole render loop through it), making canvas
  presence genuinely racy against a test's `act()` calls independent of context
  nullness. Confirmed by direct reproduction this session (not assumed). Still
  in-goal: same problem ("resolving jsdom canvas/echarts crashes"), more of it than
  the brief anticipated.
- `web/tests/DashboardView.test.tsx`: two narrow fixes to pre-existing test-fixture
  defects that were masked by the canvas crash and only surfaced once it was fixed
  (see "Rejected or changed" below for detail and why these were judged in-goal
  rather than out-of-scope).
- No `web/src/**` changes. No new dependency. No `@testing-library`. No new test file
  or test case beyond what already existed.

No unrequested "improvements" made it into the final diff — an animation-disable
experiment (`echarts.registerPreprocessor`) was tried mid-build and reverted after
producing no measurable benefit; it is not present in the diff above.

PASS.

## 3. The eval or test passed
No LLM/prompt/pipeline change this slice, so no eval run required. Done-check run
fresh at gate time:
```
$ cd web && npm test

> web@0.0.0 test
> vitest run


 RUN  v4.1.10 C:/Users/AmanRoland/Downloads/insightpilot/web

 Test Files  10 passed (10)
      Tests  149 passed (149)
   Start at  15:36:11
   Duration  63.42s (transform 1.33s, setup 453ms, import 2.47s, tests 61.44s, environment 13.43s)
$ echo $?
0
```
Every test in `DashboardView.test.tsx` passes, alongside all previously-passing files
(`SqlDetails.test.tsx`, `FollowUpChips.test.tsx`, `App.test.tsx`, all 5 `api.*.test.ts`
files). PASS.

## 4. The no-slop review found no unresolved issues
Two independent no-slop-reviewer passes were run (pre-gate and gate-time), each
reading the diff fresh rather than trusting the other's description.

**Pre-gate pass** found:
1. Comment overclaim on `CANVAS_2D_METHODS` ("not a guess... every call site") when
   two real call sites (`ctxBack.scale`, `_ctx.arcTo`) used differently-named context
   variables the grep missed. **Fixed**: added `arcTo`/`scale` to the method list and
   reworded the comment to state precisely what was grepped.
2. Minor duplication in `dragCardOnto`'s three dispatch blocks (letter-of-the-rule,
   not filed as blocking). Left as-is at that point.

**Gate-time pass** (independent, did not trust the pre-gate description) found:
1. The pre-gate fix for finding 1 was verified correctly applied, but the reworded
   comment still claimed "every `ctx.<method>(` call site" when one more (`layer.ctx.draw`,
   guarded by `if (layer.ctx.draw)`, harmless but still a literal gap) was missing.
   **Fixed**: added `draw` to the method list and adjusted the comment.
2. The same duplication in `dragCardOnto`, raised again. **Fixed**: extracted
   `actDispatchDragEvent(el, type, dataTransfer)` and reduced `dragCardOnto` to three
   one-line calls.
3. Flagged the two `DashboardView.test.tsx` changes (mock-factory `errorMessage`
   passthrough; `dragCardOnto`'s three-`act()` split) as category-8 scope concerns,
   since the brief's Outputs said the test file should stay unmodified and the
   reviewer — reading only the files on disk, not this conversation — had no written
   record that these were flagged to and approved by the user mid-build. **Resolved
   by this gate record**: see "Rejected or changed" below, which is exactly the
   written record the reviewer found missing.

Both passes independently confirmed clean: no dead code, no unhandled errors, no
naming issues, consistent with codebase style, no fake-done markers, done-check
genuinely run (not claimed). Re-ran `npm test` after each round of fixes; 149/149
passed each time.

No unresolved findings remain. PASS.

## 5. The shipping proof is attached
This slice touched zero `web/src/**` files, so the meaningful "not just tests" proof
is that the real app still builds and serves correctly (catching the "tests green
but app broken" gap this check exists for):
```
$ npm run build
✓ 628 modules transformed.
✓ built in 7.01s
```
```
$ npm run dev -- --port 5183   (started, curled, then stopped)
VITE v8.2.0  ready in 591 ms
➜  Local:   http://localhost:5183/
$ curl -s -o /dev/null -w "HTTP_STATUS:%{http_code}\n" http://localhost:5183/
HTTP_STATUS:200
```
Also ran `npx tsc --noEmit -p tsconfig.json` as an additional sanity check (not
required by this brief's done-check): exit 0, no type errors.

PASS.

## Rejected or changed
Three things were rejected or changed from the initial plan/first attempt, each
explicitly surfaced to and approved by the user before being applied — named here in
full since this is the first written record of them (the gate-time no-slop reviewer
correctly flagged their absence from any prior artifact):

1. **`vi.mock('../src/api', ...)` was missing the real `errorMessage` export.**
   `DashboardView.tsx` imports and calls a real `errorMessage(e)` util (present since
   the very first commit that created the component, `6f04d37`) in five rejection
   handlers. The test file's mock factory only ever stubbed the five API functions,
   never `errorMessage` — a defect present in the test file since its first version,
   invisible until the canvas-context fix let execution reach those rejection paths
   for the first time. Surfaced to the user with the exact failure evidence and the
   proposed one-line fix (switch the mock factory to spread `importOriginal()`,
   overriding only the five functions that need mocking) before applying it. This is
   a fixture-completeness fix, not a weakened assertion — every existing expectation
   in the file is unchanged.
2. **`dragCardOnto` batched all three drag events into one `act()` block.** Confirmed
   by isolated reproduction that this made `onDrop`'s `handleDrop` read a stale,
   pre-`setDraggedCardId` value under React 18's automatic batching, so
   `repositionCard` never fired — a bug in the test helper's event-dispatch timing
   (not in `DashboardView.tsx`'s real drag behavior, which is correct for an actual
   user drag where dragstart/dragover/drop are separate event-loop ticks). User
   explicitly rejected the first, minimal proposed fix ("no make the tests proper")
   and asked for the more thorough version, which is what shipped: three separate
   `act()` calls, later deduped into a small `actDispatchDragEvent` helper at
   gate-time no-slop's request.
3. **An `echarts.registerPreprocessor` animation-disable experiment was tried and
   reverted.** Attempted mid-build to address the ~63s vs. pre-slice ~2.6s suite
   slowdown (see below). Gave no measurable speedup even after fixing a self-inflicted
   import-ordering bug, and added a global side effect (mutating shared `echarts`
   state across every test) for no benefit. Not present in the final diff.

**Accepted, documented trade-off**: `cd web && npm test` now takes ~63s versus the
pre-slice ~2.6s. Root cause: canvas-rendering tests now actually run echarts'
default ~1000ms entrance-animation frame loop to completion (via the rAF-as-microtask
patch) instead of crashing before reaching it or racing against real timers. The
brief had no performance constraint, and the alternative (disabling animation
globally) was tried and didn't help — see item 3 above. Flagged here rather than
silently absorbed.

## Verdict
accept
