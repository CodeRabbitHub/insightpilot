# Slice log — sql-explanation-viewer

Date: 2026-08-06
Brief: plans/briefs/2026-08-06-sql-explanation-viewer.md

## The plan you approved

Extend `asAssistantContent()` (`web/src/api.ts`) with `sql`/`explanation`
using the same guard-clause style as the existing `rows`/`chartSpec`
checks, add a new `SqlDetails.tsx` using a native `<details>/<summary>`
(zero new state, matches the codebase's current avoidance of `useState`
for view-toggles), and wire it into `App.tsx`'s per-message loop
alongside the existing chart.

## The diff you accepted

Commit `865d30d` — "Render SQL and explanation in a collapsed View SQL
section per message." 8 files changed, 557 insertions(+), 4 deletions(-):
`web/src/api.ts`, `web/src/App.tsx`, new `web/src/components/SqlDetails.tsx`,
new `web/tests/api.asAssistantContent.test.ts` +
`web/tests/SqlDetails.test.tsx`, plus the brief/design-note/review-record
files. Full stat in `plans/logs/_auto-capture.md`.

## The done-check output

```
$ cd web && npm run build
✓ 626 modules transformed.
✓ built in 2.00s
```

Live Playwright run against the real dev server + real API + real
Postgres, conversation id 394 (post-refactor):
```
{
  "openBefore": false,
  "preTextBefore": 1,
  "openAfter": true,
  "sqlText": "SELECT COUNT(*) FROM olist.orders WHERE order_status = 'delivered'",
  "explanationText": "The query counted all rows in olist.orders where order_status equals 'delivered', returning a single scalar value of 96,478. This directly answers the question by giving the total count of delivered orders in the dataset.",
  "consoleErrors": []
}
```
Plus a second conversation (393) confirming the SQL section coexists
correctly with a real rendered bar chart (`canvasCount: 1, summaryCount:
1`, zero console errors) — full detail in
`artifacts/reviews/2026-08-06-sql-explanation-viewer.md`.

## One thing you rejected or changed

The brief suggested a separate `AssistantSql` sibling helper mirroring
`AssistantChart`. The no-slop pass caught that this would be the second
near-identical per-message helper independently re-resolving
`asAssistantContent()` for the same message — flagged as the start of a
copy-paste pattern the very next slice (follow-up chips) would make a
third instance of. Changed to a single `AssistantResult` helper that
resolves once and renders both `ChartView` and `SqlDetails`. Re-verified
with a fresh build and a fresh live Playwright run after the change —
behavior unchanged. Not treated as a second occurrence of a *specific*
recurring mistake worth promoting to a standing rule (duplication is
already a standard no-slop checklist category doing its job here, not a
gap in the process) — no promotion made this slice.

## The next smallest slice

Render `analysis.follow_ups` as clickable chips beneath each assistant
message that populate the compose input — the last named piece of M5
before the project moves to M6 (dashboard).
