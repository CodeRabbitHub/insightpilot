# Slice log — dashboardview-canvas-stub

Date: 2026-08-08
Brief: plans/briefs/2026-08-08-dashboardview-canvas-stub.md

## The plan you approved

Add a `HTMLCanvasElement.prototype.getContext('2d')` stub to `web/tests/setup.ts`
(no-op implementations of every canvas method reachable from zrender/echarts source,
verified by grepping `node_modules` rather than guessed), returning the same cached
stub per canvas via a `WeakMap`. No new dependency, no `web/src/**` changes, no
weakening of `DashboardView.test.tsx`'s deliberate real-`<canvas>` proof (no mocking
`ChartView`/`echarts-for-react`).

## The diff you accepted

Commit `573308f` — "Stub jsdom's missing 2D canvas context and real-timer rAF so
DashboardView.test.tsx passes for real." Full mechanics in
`plans/logs/_auto-capture.md`. Final diff: `web/tests/setup.ts` (+100) and
`web/tests/DashboardView.test.tsx` (+44/-12), plus this slice's own brief and gate
record.

The approved plan covered the canvas-context stub; the actual diff also needed a
`requestAnimationFrame`-to-microtask patch (canvas creation was independently gated
behind a real-timer-driven animation loop, not just context nullness — discovered
during BUILD, confirmed by direct reproduction, not assumed) and two narrow
test-fixture fixes surfaced only once the crash stopped masking them. See gate
record's "Rejected or changed" for the full account of why each was judged in-goal.

## The done-check output

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
Every test in `DashboardView.test.tsx` passes, alongside all previously-passing
files. Full gate record (all five checks, two independent no-slop passes, shipping
proof): `artifacts/reviews/2026-08-08-dashboardview-canvas-stub.md`.

## One thing you rejected or changed

I proposed the minimal fix for the drag-reposition test failures: split
`dragCardOnto`'s single `act()` block into three, one per event, to fix the React 18
batching bug where `onDrop` read a stale `draggedCardId`. You rejected accepting that
as-is ("no make the tests proper") and asked for the fix to be done properly rather
than as a narrow patch. In response I re-verified the fix was structurally correct
(not just accepted it), then at gate-time no-slop's request also deduped the three
near-identical `act()` blocks into a small `actDispatchDragEvent` helper, so the final
version is both correct and clean rather than a bare minimal patch. This is the first
occurrence of this specific pattern (reject a working-but-minimal fix, ask for the
thorough version) in this project's logs — not yet a second repetition, so no
CLAUDE.md/no-slop.md promotion proposed; worth watching if it recurs.

Also notable: an `echarts.registerPreprocessor` animation-disable experiment was
tried mid-build to address the test-suite slowdown, then reverted after it gave no
measurable benefit and added a global side effect for nothing — good instinct to
verify empirically before committing to an optimization, worth repeating next time
a "should be faster" idea comes up.

## The next smallest slice

Investigate and fix the ~63s vs. pre-slice ~2.6s `DashboardView.test.tsx` suite
slowdown (canvas-rendering tests now run echarts' full ~1000ms entrance-animation
frame loop via the rAF-as-microtask patch) without reintroducing the raciness this
slice just fixed — the `registerPreprocessor` route tried this session didn't help,
so the next attempt needs a different angle (e.g. patching the animation clock
itself, or scoping animation-disable to only the chart's own `setOption` call rather
than globally).
