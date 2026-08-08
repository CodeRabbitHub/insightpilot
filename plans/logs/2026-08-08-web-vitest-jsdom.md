# Slice log — web-vitest-jsdom

Date: 2026-08-08
Brief: plans/briefs/2026-08-08-web-vitest-jsdom.md

## The plan you approved

Add `vitest` + `jsdom` as the only two new devDependencies; wire jsdom via
a new, separate `web/vitest.config.ts` (not merged into `vite.config.ts`,
keeping the production build config untouched); add an `npm test` script
(`vitest run`); run the suite and confirm `SqlDetails.test.tsx`/
`FollowUpChips.test.tsx` pass without touching any test assertions.

## The diff you accepted

Commit `7e04895` — "Wire vitest + jsdom into web/, get SqlDetails/
FollowUpChips tests running". 6 files changed, 1107 insertions(+), 3
deletions(-): `web/package.json`, `web/package-lock.json` (npm-generated),
new `web/vitest.config.ts`, new `web/tests/setup.ts`, plus this slice's own
brief and gate record. Full stat and message: `plans/logs/_auto-capture.md`
("Commit at 2026-08-08 14:12").

## The done-check output

Scoped run (the brief's actual pass criterion):
```
$ cd web && npx vitest run --reporter=verbose tests/SqlDetails.test.tsx tests/FollowUpChips.test.tsx
 Test Files  2 passed (2)
      Tests  16 passed (16)
exit code: 0
```

Full-directory run (brief's literal done-check command):
```
$ cd web && npm test
 Test Files  1 failed | 9 passed (10)
      Tests  41 failed | 108 passed (149)
exit code: 1
```
Only `tests/DashboardView.test.tsx` fails (count varies run-to-run, 34-46
of 149, because the failures are async unhandled-rejection races inside
echarts' own canvas teardown under jsdom's missing `getContext` — an
inherent property of that file's known, brief-accepted out-of-scope
fragility). `App.test.tsx` and all 5 `api.*.test.ts` files pass every run.
Full detail and the no-slop reviewer's independent re-verification:
`artifacts/reviews/2026-08-08-web-vitest-jsdom.md`.

## One thing you rejected or changed

The pre-gate no-slop review found a silent, unacknowledged
`Warning: The current testing environment is not configured to support
act(...)` firing on every single test in the suite (nothing set
`globalThis.IS_REACT_ACT_ENVIRONMENT`). Rather than accepting this as a
written exception, it was fixed: added `web/tests/setup.ts` (sets the
flag, with a one-line why-comment) wired via `vitest.config.ts`'s
`setupFiles`. A fresh, independent gate-time no-slop pass re-verified the
fix directly (ran the tests itself, grepped for the warning text, zero
matches) before sign-off. First occurrence of this specific finding — no
ratchet promotion needed yet.

## The next smallest slice

Get `DashboardView.test.tsx`'s canvas-related failures fixed by stubbing/
mocking the canvas 2D context (`HTMLCanvasElement.prototype.getContext`)
in the test environment so `echarts`/`echarts-for-react` don't crash under
jsdom's unimplemented canvas — no new npm dependency (specifically, not
the `canvas` native package).
