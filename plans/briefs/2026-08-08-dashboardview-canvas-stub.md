# Brief — dashboardview-canvas-stub

Date: 2026-08-08
Milestone: M6 Dashboard (test infrastructure for existing, previously-unexecuted frontend tests)

Goal:
Get `web/tests/DashboardView.test.tsx` passing for real by resolving its
jsdom canvas/echarts crashes, without weakening its real-`<canvas>`-DOM-
node proof of per-card chart invocation.

Constraints:
- No new npm dependency — specifically not the native `canvas` package
  (explicit user decision from the prior session, HANDOFF.md). Any fix
  must live in test infrastructure (e.g. a `getContext` stub added via
  `web/tests/setup.ts` or `web/vitest.config.ts`), not a new dependency.
- Do not modify `DashboardView.test.tsx`'s assertions to make failures
  disappear (CLAUDE.md: never weaken a test to make it pass).
- Preserve this test file's deliberate design choice not to mock
  `ChartView`'s rendering (its own header comments, ~lines 27-34, 60-64):
  the real `<canvas>` DOM node appearing must remain genuine proof of
  per-card chart invocation, not an assumption. If the only viable fix
  requires mocking `ChartView` or `echarts-for-react` instead of stubbing
  the canvas context, stop and flag that trade-off at Gate 1 rather than
  adopting it silently — it changes what the test actually proves. That
  conclusion, if reached, is a legitimate Gate 1 finding, not a
  constraint violation.
- No changes to `web/src/**` application code — `DashboardView.tsx`/
  `ChartView.tsx` are correct in production; this is a test-environment
  gap only.
- Match existing house style: no `@testing-library`.

Inputs:
- `web/tests/DashboardView.test.tsx` (unmodified since a prior slice) and
  its call-through `ChartView` spy design.
- Two known failure modes captured from real runs last session:
  1. `Not implemented: HTMLCanvasElement's getContext() method: without
     installing the canvas npm package`, cascading into `TypeError: Cannot
     read properties of null (reading 'clearRect')` inside echarts' own
     `Layer`/`CanvasPainter`/`ZRender` dispose+refresh code.
  2. `[ECharts] Can't get DOM width or height...` — a console warning
     (not confirmed fatal) from jsdom's lack of real layout.
- `web/vitest.config.ts` and `web/tests/setup.ts` (added last slice) as
  the natural place for any environment-level stub.
- Prior evidence: `plans/logs/2026-08-08-web-vitest-jsdom.md` and
  `artifacts/reviews/2026-08-08-web-vitest-jsdom.md` (exact stack traces,
  flakiness pattern — the failing-test list shifts run to run because
  these are async unhandled-rejection races, not deterministic
  single-point failures).

Outputs:
- A canvas 2D context stub (or equivalent test-environment fix), wired via
  `web/tests/setup.ts` or `web/vitest.config.ts`, sufficient for
  `echarts`/`echarts-for-react` to mount and dispose without throwing.
- `web/tests/DashboardView.test.tsx` passing for real, unmodified.

Done-check:
`cd web && npm test` runs to completion, exit code 0, with output showing
every test in `DashboardView.test.tsx` passing alongside all previously-
passing files (`SqlDetails.test.tsx`, `FollowUpChips.test.tsx`,
`App.test.tsx`, all 5 `api.*.test.ts` files). Paste the full terminal
output.

Out-of-scope:
- Adding the `canvas` npm package or any other new dependency.
- Modifying `DashboardView.test.tsx`'s or `DashboardView.tsx`'s/
  `ChartView.tsx`'s real code/assertions to force failures away.
- Chasing the `[ECharts] Can't get DOM width or height` console warning
  into a full jsdom layout-engine fix if it turns out to be non-fatal
  noise once the canvas-context stub is in place — flag it as accepted
  residual noise instead.
- ESLint/ruff/mypy tooling, CI wiring — separate, unaddressed items.
- Any new test file or new test case beyond what already exists in
  `DashboardView.test.tsx`.
