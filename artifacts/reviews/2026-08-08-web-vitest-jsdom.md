# Review gate — web-vitest-jsdom

Date: 2026-08-08
Brief: plans/briefs/2026-08-08-web-vitest-jsdom.md
Diff reviewed: working tree (web/package.json, web/package-lock.json, web/vitest.config.ts, web/tests/setup.ts) — pre-commit

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review

```
 web/package-lock.json | 918 +++++++++++++++++++++++++++++++++++++++++++++++++-
 web/package.json      |   7 +-
 web/tests/setup.ts    |   4 +
 web/vitest.config.ts  |  10 +
 4 files changed, 936 insertions(+), 3 deletions(-)
```

The lockfile diff is npm-generated (transitive deps of `vitest`/`jsdom` only —
spot-checked, no stray packages). The hand-authored diff is 21 lines across
three files, shown and read in full. PASS.

## 2. The stated goal matches the actual change

Goal: wire `vitest` + jsdom into `web/package.json`, get
`SqlDetails.test.tsx`/`FollowUpChips.test.tsx` passing for real.

Diff: adds `vitest`+`jsdom` devDependencies, an `npm test` script, a new
`vitest.config.ts` (jsdom environment, same `react()` plugin as
`vite.config.ts`), and one addition beyond the brief's literal text —
`web/tests/setup.ts` (sets `IS_REACT_ACT_ENVIRONMENT`) — added mid-gate to
fix a no-slop finding (an unacknowledged `act()` warning on every test), not
speculative scope creep. No new dependency, no test-assertion changes. PASS.

## 3. The eval or test passed

Scoped run (the brief's actual pass criterion), fresh:
```
$ cd web && npx vitest run --reporter=verbose tests/SqlDetails.test.tsx tests/FollowUpChips.test.tsx
 Test Files  2 passed (2)
      Tests  16 passed (16)
exit code: 0
```

Full-directory run (brief's literal done-check command), fresh:
```
$ cd web && npm test
 Test Files  1 failed | 9 passed (10)
      Tests  41 failed | 108 passed (149)
exit code: 1
```
Only `tests/DashboardView.test.tsx` fails, every run (34/149, 46/149, 41/149,
36/149 across four independent runs this session — the count itself is
flaky because the failures are async unhandled-rejection races inside
echarts' own canvas teardown under jsdom's missing `getContext`, an inherent
property of that file's known-out-of-scope fragility, not this diff).
`App.test.tsx` and all 5 `api.*.test.ts` files pass every run. The brief's
done-check text says "exit code 0" but `vitest run` exits 1 whenever any
file in the shared invocation fails — the accurate framing is: the two
target files pass with exit 0 in isolation; the full-suite command exits 1
with the single failure being the explicitly accepted out-of-scope file.
Production build regression-checked, unaffected:
```
$ cd web && npm run build
✓ 628 modules transformed.
✓ built in 856ms
```
PASS.

## 4. The no-slop review found no unresolved issues

Pre-gate pass (no-slop-reviewer subagent) found one finding: every test
printed `Warning: The current testing environment is not configured to
support act(...)` because nothing set `IS_REACT_ACT_ENVIRONMENT` — logged
and left, uncategorized in the diff. Fixed by adding `web/tests/setup.ts`
+ `vitest.config.ts`'s `setupFiles`.

Gate-time pass (independent, fresh no-slop-reviewer subagent) verified the
fix directly (ran the target tests itself, grepped for the warning text —
zero matches) and found zero new findings. Two purely informational notes
(a separate pre-existing `ReactDOMTestUtils.act` deprecation warning
inherent to the test files' existing house-style import, untouched by this
diff; and `tsconfig.node.json` not extended to cover the new
`vitest.config.ts`, cosmetic only, build unaffected) — neither is a rubric
violation, both explicitly called out as non-findings by the reviewer.
PASS.

## 5. The shipping proof is attached

No user-facing surface (test-infra slice) — proof is the real `npm test`/
`npm run build` output above, run against this machine's actual
`node_modules`, not mocked. PASS.

## Rejected or changed

The pre-gate no-slop finding (silent `act()` warning) was not accepted as a
written exception — fixed with `web/tests/setup.ts` instead of leaving it
unaddressed.

## Verdict

accept — all five checks pass.
