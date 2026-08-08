# Brief — web-vitest-jsdom

Date: 2026-08-08
Milestone: M5 Chat UI (test infrastructure for existing, previously-unexecuted frontend tests)

Goal:
Wire `vitest` + a jsdom test environment into `web/package.json` and get
`SqlDetails.test.tsx` and `FollowUpChips.test.tsx` passing for real, as the
project's first frontend test run that actually executes.

Constraints:
- New devDependencies limited to `vitest` and a jsdom environment package
  (`jsdom` itself, or `@vitest/environment-jsdom` if vitest's version
  requires it) — nothing else. User sign-off for this new dependency was
  already given in the prior session (see HANDOFF.md). No
  `@testing-library` or any other test-utility library: house style
  (all four existing test files) renders via `react-dom/client`'s
  `createRoot` + `act` from `react-dom/test-utils` directly, and that
  style must keep working unchanged.
- jsdom environment wired via either `vite.config.ts`'s `test` block or a
  new `vitest.config.ts` — one or the other, not both.
- A real `npm test` script in `web/package.json` must invoke vitest
  against the whole `web/tests/` directory.
- Do not modify `SqlDetails.test.tsx`'s or `FollowUpChips.test.tsx`'s
  assertions to make them pass (CLAUDE.md: never weaken a test to make it
  pass). If a real component bug surfaces, fix the component; if a test
  itself has a genuine defect, flag it rather than silently loosening it.
- `web/tsconfig.app.json`'s `"include": ["src"]` currently excludes
  `web/tests/*.test.tsx` from `tsc -b`'s production type-check. Don't fold
  test files into that scope without flagging it as a deliberate decision
  at Gate 1.

Inputs:
- `web/package.json`'s current devDependencies (vite, typescript,
  @vitejs/plugin-react, Tailwind toolchain — no test runner yet).
- `web/tests/SqlDetails.test.tsx` (126 lines) and
  `web/tests/FollowUpChips.test.tsx` (135 lines) — the two simplest of the
  four existing test files (no `vi.mock` module factories, no drag
  events, no canvas-rendering components).
- `web/tests/DashboardView.test.tsx` and `web/tests/App.test.tsx` exist in
  the same directory but are explicitly not this slice's job (see
  Out-of-scope) — both already flag jsdom `DragEvent`/canvas/StrictMode
  timing risk in their own header comments.

Outputs:
- `web/package.json` with `vitest` + a jsdom environment as new
  devDependencies and a working `npm test` script.
- A vitest config (in `vite.config.ts` or a new `vitest.config.ts`)
  configured for the jsdom environment.
- `SqlDetails.test.tsx` and `FollowUpChips.test.tsx` passing, for real.

Done-check:
`cd web && npm test` runs to completion, exit code 0, with output showing
every test in `SqlDetails.test.tsx` and `FollowUpChips.test.tsx` passing.
Paste the full terminal output. `DashboardView.test.tsx`/`App.test.tsx`
will run as part of the same vitest invocation since they share the
directory — if either fails, that output must be shown too and called out
explicitly as known-out-of-scope, not hidden.

Out-of-scope:
- Making `DashboardView.test.tsx` or `App.test.tsx` pass — both carry
  known jsdom-fragility risk (drag events, canvas rendering, real
  `<StrictMode>` double-invoke timing). A follow-on slice, once the runner
  itself is proven, is the right size for that.
- `@testing-library` or any test-utility library beyond vitest + jsdom.
- CI / GitHub Actions wiring for the new test script.
- ESLint/ruff/mypy tooling.
- Any new test file or test case beyond what already exists in
  `SqlDetails.test.tsx`/`FollowUpChips.test.tsx`.
