# Slice log — follow-up-chips

Date: 2026-08-06
Brief: plans/briefs/2026-08-06-follow-up-chips.md

## The plan you approved

Extend `asAssistantContent()` (`web/src/api.ts`) with `followUps`
using the same `Array.isArray` guard-clause style already used for
`rows`, add a new `FollowUpChips.tsx` (one pill button per entry, renders
nothing when empty), and wire its `onSelect` through `AssistantResult`
into `ConversationDetailView`'s existing `question`/`setQuestion` state —
no new state store.

## The diff you accepted

Commit `1ba4dc0` — "Render analysis.follow_ups as clickable chips beneath
each message." 7 files changed, 450 insertions(+), 4 deletions(-):
`web/src/api.ts`, `web/src/App.tsx`, new `web/src/components/FollowUpChips.tsx`,
new `web/tests/FollowUpChips.test.tsx` + additions to
`web/tests/api.asAssistantContent.test.ts`, plus the brief and review
record.

## The done-check output

```
$ cd web && npm run build
> web@0.0.0 build
> tsc -b && vite build
✓ 627 modules transformed.
✓ built in 1.89s
```

Live Playwright run against the real dev server, real API, real
Postgres, real headless Chromium, driven through the actual chat UI
(conversation #394):
```
{
  "question": "What was the total revenue from delivered orders in 2018?",
  "newChipCount": 5,
  "newChipTexts": [
    "How does 2018 delivered revenue compare to 2017 revenue?",
    "What was the monthly trend of delivered order revenue in 2018?",
    "Which product categories contributed the most revenue in 2018?",
    "What percentage of total 2018 orders were delivered versus cancelled or other statuses?",
    "What was the average order value for delivered orders in 2018?"
  ],
  "beforeInputValue": "",
  "clickedText": "What was the average order value for delivered orders in 2018?",
  "afterInputValue": "What was the average order value for delivered orders in 2018?",
  "matches": true,
  "consoleErrors": []
}
```
Compose input was empty before the click, held the exact clicked chip's
text after, and no new message was sent (no auto-submit). Full detail
and screenshots in `artifacts/reviews/2026-08-06-follow-up-chips.md`.

## One thing you rejected or changed

The doc comment above `asAssistantContent()` in `api.ts` named
"ChartView and SqlDetails" as the check's consumers — stale the moment
`FollowUpChips` became a third consumer. This is the *second* time this
exact comment has gone stale from naming specific callers (first: the
prior slice's gate fixed it from naming only `ChartView` to naming
`ChartView and SqlDetails`). Fixed this time by generalizing it to "any
per-message assistant component," and promoted the pattern to
`templates/no-slop.md` §6 so it's checked on every future review instead
of relying on each gate catching it by hand.

## The next smallest slice

M5 (Chat UI) is now fully done — chart, SQL viewer, and follow-up chips
all shipped. M6 (Dashboard) starts with the smallest useful cut: add a
"Pin to dashboard" action on assistant messages that persists the
answer (no dashboard page/grid yet — that's the slice after).
