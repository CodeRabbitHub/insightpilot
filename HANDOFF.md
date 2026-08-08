# Handoff

Date: 2026-08-08
Slice just completed: plans/briefs/2026-08-08-dashboardview-canvas-stub.md
  + plans/logs/2026-08-08-dashboardview-canvas-stub.md
  (commit 573308f, gate record artifacts/reviews/2026-08-08-dashboardview-canvas-stub.md)

## State of the work

- **`web/tests/DashboardView.test.tsx` passes for real, in full — all 149 tests
  across all 10 files pass.** The DashboardView-specific failures that every prior
  handoff carried forward as an open, accepted-out-of-scope gap are now resolved.
- **Two genuine root causes were fixed in `web/tests/setup.ts`**, not one:
  1. jsdom's `HTMLCanvasElement.getContext('2d')` returns `null` without the native
     `canvas` package (still deliberately not added). A stub now returns a
     per-canvas-cached (via `WeakMap`) plain object implementing every canvas 2D
     method reachable from `zrender`/`echarts` source — verified by grepping
     `node_modules/{zrender,echarts}/lib` directly (two rounds of independent
     no-slop review each found one real gap in that list — `arcTo`/`scale` via
     differently-named context variables, then `draw` — both now covered).
  2. Independently of context nullness: `zrender` captures `window.requestAnimationFrame`
     once at its own module-load time and drives its entire render/animation loop
     through it. jsdom's rAF is a real ~16ms wall-clock timer, so a chart's first
     `<canvas>` only appeared after real time passed — genuinely racing against a
     test's synchronous `act()` calls. Confirmed by direct reproduction this
     session (not assumed). Fixed by patching `globalThis.requestAnimationFrame` to
     resolve via `queueMicrotask`, set in `setup.ts` specifically because it must
     run before any module transitively imports `zrender` (a patch applied later,
     e.g. inside a test body, has no effect on the reference `zrender` already
     captured — confirmed the hard way, via a self-inflicted repeat of this exact
     bug mid-session when an experiment added a static `import` of `echarts` to
     `setup.ts`, which hoists above the patch statement).
- **Two pre-existing test-fixture defects in `DashboardView.test.tsx` were also
  fixed**, both masked by the canvas crash until it stopped happening, both
  confirmed by isolated reproduction and explicitly approved before being applied:
  1. `vi.mock('../src/api', ...)` never stubbed the real `errorMessage` export that
     `DashboardView.tsx` imports and calls in five rejection handlers — present
     since the component's first commit, invisible until execution could reach
     those catch blocks. Fixed by switching the mock factory to spread
     `importOriginal()` and override only the five functions that need mocking.
  2. `dragCardOnto` dispatched `dragstart`/`dragover`/`drop` inside one shared
     `act()` block. React 18 batches the `setDraggedCardId` state update from
     `dragstart` within that block, so `onDrop`'s `handleDrop` read a stale
     (`null`) `draggedCardId` and never called `repositionCard` — a test-timing
     bug, not a `DashboardView.tsx` bug (real browser drags fire these as separate
     event-loop ticks). Fixed by giving each event its own `act()` call, then
     deduping the three into a small `actDispatchDragEvent` helper at gate-time
     no-slop's request.
- **No `web/src/**` changes, no new dependency, no `@testing-library`.** Diff
  confined to `web/tests/setup.ts` (+100) and `web/tests/DashboardView.test.tsx`
  (+44/-12), plus this slice's own brief/log/gate-record files.
- **Two independent no-slop passes, all findings fixed** (record:
  `artifacts/reviews/2026-08-08-dashboardview-canvas-stub.md`). Nothing carried as
  an unresolved exception.
- **New, accepted trade-off: `cd web && npm test` now takes ~63s, up from the
  pre-slice ~2.6s.** Canvas-rendering tests now actually run echarts' default
  ~1000ms entrance-animation frame loop to completion (via the rAF-as-microtask
  patch) instead of crashing or never reaching that code. An
  `echarts.registerPreprocessor((option) => { option.animation = false })`
  experiment was tried mid-session to eliminate this and gave no measurable
  improvement even after fixing its own import-ordering bug — reverted, not in the
  final diff. This is now the seed of the next slice below.
- Production build (`npm run build`) and a real `vite` dev server (started,
  confirmed `HTTP_STATUS:200`, then stopped) both verified unaffected — expected,
  since no `web/src/**` file changed, but confirmed rather than assumed.

## Proof

Full-directory run (brief's literal done-check command), run fresh at gate time:
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

Production build:
```
$ npm run build
✓ 628 modules transformed.
✓ built in 7.01s
```

Real dev server (shipping proof, since no `src/**` changed):
```
$ npm run dev -- --port 5183
VITE v8.2.0  ready in 591 ms
➜  Local:   http://localhost:5183/
$ curl -s -o /dev/null -w "HTTP_STATUS:%{http_code}\n" http://localhost:5183/
HTTP_STATUS:200
```
(Verified stopped afterward — the first `kill` attempt during the session silently
failed to actually terminate the background process; caught and fixed by checking
port 5183 again before writing this handoff, rather than assuming the kill worked.)

## Open questions / known issues

- Carried over, unchanged from the previous handoff (still true, still
  unaddressed):
  - `chart_spec` still has no fixed schema by design
    (`prompts/analyze.md`); `ChartView.tsx`'s alias-resolution approach
    remains the frontend's answer to this.
  - ECharts auto-hides overlapping x-axis category labels under narrow
    container widths — not a bug, unaddressed by design.
  - No charting library styling beyond a single fixed accent color; no
    dark mode; no table-view toggle.
  - Decimal-valued rows still serialize as JSON strings, not numbers, in
    the raw `<pre>` dump (conversations view only).
  - `NullPool` needs re-evaluation under uvicorn's single persistent
    event loop — still flagged in `app/db/session.py`'s own comment.
  - What happens to an already-computed answer when its persistence
    write fails: still a plain 500 / silently truncated SSE stream.
  - `tests/test_seed_idempotency.py`'s own real Postgres deadlock
    (M1-era, unrelated code) remains uninvestigated.
  - Lint/type tooling on the Python side (`ruff`, `mypy`) remains
    unaddressed.
  - A `response.content[0].text`/`ThinkingBlock` bug pattern is fixed
    only in `analyze_answer.py`; `generate_sql.py`, `repair_sql.py`,
    `describe.py` still carry the same fragile assumption. (Considered as
    this slice's follow-on and explicitly deferred in favor of the test-suite
    speed slice below — still open, still worth picking up soon.)
  - The project's own `.venv` (Python 3.11.15) must be used explicitly
    for backend commands.
  - API base URL is a hardcoded `http://localhost:8000` constant in
    `web/src/api.ts`.
  - `Conversation`'s `user_id` FK to `users` is deliberately omitted --
    `users` doesn't exist yet (F8).
  - `queries` table (PRD §7's fourth `app`-schema table) still doesn't
    exist -- not needed until the pipeline-logging slice.
  - Docker Desktop's daemon does not auto-start with this
    machine/session -- if a session's done-check fails with a Postgres
    connection refusal on port 5433, start Docker Desktop and run
    `docker compose up -d` before assuming a code regression.
  - The dev Postgres `dashboards`/`dashboard_cards` tables have
    accumulated leftover proof/test cards from prior sessions' real-
    server shipping proofs (harmless; still worth a cleanup pass
    eventually).
  - A `uvicorn` dev server (port 8000) may still be up from earlier
    sessions (not touched this slice). This slice's own `vite` dev server
    (port 5183) was explicitly started and stopped for shipping proof --
    confirmed actually stopped before this handoff was written, not assumed.
  - `plans/logs/2026-08-07-run-dashboard-card-endpoint.md` still sits
    untracked in the working tree (a leftover from a session several
    slices back whose capture commit was apparently skipped). Still out
    of every subsequent slice's scope; still worth a deliberate small
    cleanup commit eventually.
  - `get_dashboard`'s `ORDER BY DashboardCard.position` (`app/main.py:380`)
    still has no secondary sort key. Still just an observation, not
    fixed.
  - The DB-drift-on-partial-`repositionCard`-failure tradeoff from the
    drag-reposition slice remains an accepted, documented known
    limitation -- not tracked as a bug to fix.
  - ESLint tooling remains unaddressed (separate from the now-resolved
    frontend-test-runner gap).
  - A stray `web/.claude/.last_verified_signature` file is untracked
    again this session (hook-generated state; root `.gitignore`'s
    pattern doesn't match nested paths). This is now the **second**
    consecutive handoff to note it -- ratchet-eligible (a one-line
    `.gitignore` addition, e.g. `**/.claude/.last_verified_signature`),
    but still not fixed, since it was out of scope for this slice too.
    Next session that touches `.gitignore` or notices it a third time
    should just fix it.
- New this slice:
  - **The `~63s` `DashboardView.test.tsx` suite runtime is the new open item** --
    see State of the work above for the root cause (real animation-frame-loop
    work, now compressed onto microtasks instead of crashing) and the failed
    `registerPreprocessor` attempt. This is the seed of the next slice below.

## Next slice (the brief, written NOW while context is hot)

Goal:
Reduce `web/tests/DashboardView.test.tsx`'s ~63s suite runtime (down from a
pre-canvas-stub ~2.6s) without reintroducing the raciness the canvas-stub slice
fixed -- every canvas-presence assertion must still pass deterministically.

Constraints:
- No new npm dependency (same standing constraint as the canvas-stub slice --
  specifically not the native `canvas` package).
- Do not modify `DashboardView.test.tsx`'s assertions, and do not reintroduce
  ChartView/echarts-for-react mocking -- the real `<canvas>` DOM node must remain
  genuine, unmocked proof of per-card chart invocation, per this file's own
  long-standing design (unchanged by the prior slice).
- No `web/src/**` changes -- `ChartView.tsx`/`DashboardView.tsx` are correct in
  production; this is a test-environment performance issue only.
- Whatever mechanism is used must not depend on echarts' internal animation
  timing being a certain duration (fragile against an echarts/zrender version
  bump) if avoidable -- prefer disabling/short-circuiting the animation loop
  itself over trying to speed-run it.
- Match existing house style in `web/tests/setup.ts` (plain patches/stubs, no new
  test-utility library).

Inputs:
- `web/tests/setup.ts`'s current `requestAnimationFrame`-as-microtask patch
  (`globalThis.requestAnimationFrame = (fn) => { queueMicrotask(() => fn(0)); return 0 }`)
  -- this is what turns the ~1000ms real-wall-clock entrance animation into a
  ~1000ms *microtask-driven* animation instead of eliminating it; the frame count
  is unchanged, only the delay between frames is compressed to ~0.
  - Note: this patch is load-bearing for correctness (see the prior slice's
    HANDOFF/log/gate record for why) -- any speed fix must keep it or replace it
    with something that preserves the same "canvas appears deterministically
    within a synchronous test's `act()` calls" guarantee, not remove it outright.
- The already-tried-and-reverted `echarts.registerPreprocessor((option) => {
  option.animation = false })` experiment (see this slice's log/gate record) --
  gave no measurable speedup even with correct import ordering, meaning the cost
  is NOT solely the chart's own data-animation. The temporary `echarts.init()`
  instance inside `echarts-for-react`'s `initEchartsInstance()`
  (`node_modules/echarts-for-react/lib/core.js`) creates a SECOND, real init cycle
  per chart mount before the real one renders -- whatever is driving the ~1s cost
  likely needs to be traced through that path too, not just the final chart's own
  `option.animation`.
- `plans/logs/2026-08-08-dashboardview-canvas-stub.md` and
  `artifacts/reviews/2026-08-08-dashboardview-canvas-stub.md` for the full prior
  investigation (rAF capture-at-module-load mechanics, the self-inflicted
  reintroduction of the bug via a static `import`, the failed
  `registerPreprocessor` attempt).

Outputs:
- `web/tests/DashboardView.test.tsx`'s full suite runtime measurably reduced from
  ~63s (target: ideally back near the ~2.6s baseline, but any honest, verified
  improvement is acceptable to report -- do not claim a number that wasn't
  actually measured).
- Every one of the 149 tests still passing, unmodified.

Done-check:
`cd web && npm test` runs to completion, exit code 0, with output showing all 149
tests passing (same set as this slice's proof) AND a `Duration` figure measurably
lower than ~63s. Paste the full terminal output including the duration line, run
at least twice to rule out one-off variance.

Out-of-scope:
- Any new npm dependency.
- Any change to `DashboardView.test.tsx`'s assertions or to `ChartView.tsx`/
  `DashboardView.tsx`.
- Mocking `ChartView`/`echarts-for-react` to skip real rendering -- if
  investigation concludes that's the only way to get meaningful speed, stop and
  flag that trade-off rather than adopting it silently (same rule as the prior
  slice).
- Chasing test-suite speed for `SqlDetails.test.tsx`/`FollowUpChips.test.tsx`/
  `App.test.tsx`/`api.*.test.ts` -- they're already fast; this is scoped to
  `DashboardView.test.tsx` specifically.
- ESLint/ruff/mypy tooling, the `ThinkingBlock` bug pattern, the stray
  `.gitignore` gap, or any other carried-over open question above.
