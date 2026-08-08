# Slice log — app-strictmode-fetch-guard

Date: 2026-08-08
Brief: plans/briefs/2026-08-08-app-strictmode-fetch-guard.md

## The plan you approved

Add the same `stale`-flag guard already used by this file's own
conversation-detail effect (and by `DashboardView.tsx`'s prior fix) to
`App.tsx`'s conversations-list mount effect. Test it by rendering a real
`<StrictMode>` wrapper directly in the test (matching `main.tsx`'s
production wrapping) rather than a prop-swap proxy, since this effect's
`[]` deps give no prop to force a second invocation.

## The diff you accepted

Commit `df51337` — "Guard App.tsx's conversations-list fetch against
StrictMode's stale double-invoke": `web/src/App.tsx` (+16/-3), new
`web/tests/App.test.tsx` (245 lines), plus this slice's brief and gate
record.

(A separate, smaller correction also happened this session: an earlier
attempt bundled this slice's changes into a commit meant only to close out
a leftover `plans/logs/_auto-capture.md` entry from the prior slice's
handoff commit. Caught before pushing anywhere — fixed via `git reset
--soft HEAD~1` (non-destructive, nothing lost) and re-committed as the
single accurate commit above.)

## The done-check output

```
> web@0.0.0 build
> tsc -b && vite build

vite v8.2.0 building client environment for production...
✓ 628 modules transformed.
✓ built in 965ms
```

Shipping proof (Playwright, route-intercepting `GET /api/conversations`,
real dev servers, StrictMode active via `main.tsx`):

Fixed code:
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

Pre-fix repro (`git stash` of just the App.tsx guard):
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
Bug reproduced for real (fresh marker gets clobbered by the late-resolving
stale response); fix reproduced again after `git stash pop`. Full record:
artifacts/reviews/2026-08-08-app-strictmode-fetch-guard.md.

## One thing you rejected or changed

The test-writer subagent's first draft of `web/tests/App.test.tsx` carried
a stale TDD-narration header comment ("written before the fix lands...")
— the **identical** defect the immediately-prior slice's own gate caught
and fixed on the sibling `DashboardView.test.tsx`, one commit later, same
subagent. Fixed (reworded to present tense) before this slice's gate
closed.

Repeat pattern, promoted per direct sign-off:
- `templates/no-slop.md` category 6 gained a new line naming this exact
  pattern (test headers must describe current behavior, not TDD
  sequencing), with both occurrences cited.
- `.claude/agents/test-writer.md` itself gained a new rule (#5) telling
  the subagent directly to write headers in present tense — since the
  source of the repeat is that specific subagent's habit, fixing its own
  instructions addresses the root cause, not just the catch.

## The next smallest slice

Wire up a real frontend test runner (`vitest` + jsdom as new
devDependencies, per direct user choice): four test files
(`SqlDetails.test.tsx`, `FollowUpChips.test.tsx`, `DashboardView.test.tsx`,
now `App.test.tsx`) have all been written correctly across multiple slices
but none can execute yet — the ratchet's 2nd-repetition threshold was
already exceeded twice over. This slice is the explicit "yes" to that new
dependency CLAUDE.md requires, plus wiring `npm test` (or equivalent) and
confirming all four existing files actually pass for real.
