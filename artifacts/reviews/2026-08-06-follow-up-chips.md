# Review gate — follow-up-chips

Date: 2026-08-06
Brief: plans/briefs/2026-08-06-follow-up-chips.md
Diff reviewed: working tree (uncommitted) — web/src/api.ts, web/src/App.tsx,
new web/src/components/FollowUpChips.tsx, web/tests/api.asAssistantContent.test.ts
(additions), new web/tests/FollowUpChips.test.tsx

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review

```
 web/src/App.tsx                          |  14 +-
 web/src/api.ts                           |   8 +-
 web/tests/api.asAssistantContent.test.ts |  85 +++++++++++
 web/src/components/FollowUpChips.tsx     (new, 23 lines)
 web/tests/FollowUpChips.test.tsx         (new)
 plans/briefs/2026-08-06-follow-up-chips.md (new)
```
4 files changed in source scope, two new source/test files. Every line
read. PASS.

## 2. The stated goal matches the actual change

Brief goal: render `analysis.follow_ups` as clickable chips beneath each
assistant message; clicking one populates (not submits) the compose
input.

Diff does exactly this:
- `api.ts`: `AssistantContent` gains `followUps: string[]`;
  `asAssistantContent()` extracts `analysis.follow_ups` with an
  `Array.isArray` guard (same looseness as the existing `rows` check),
  returning `null` for the whole object if absent/malformed — consistent
  with the existing all-or-nothing guard-clause style.
- New `FollowUpChips.tsx`: renders nothing for an empty list, one
  `<button type="button">` per entry otherwise, `onClick={() =>
  onSelect(text)}`.
- `App.tsx`: `AssistantResult` gains `onSelectFollowUp`, renders
  `FollowUpChips` after `SqlDetails`; `ConversationDetailView` wires it to
  the existing `setQuestion` — no new state store.

No extra changes: `git diff --stat -- app prompts web/package.json` is
empty. No auto-submit, no dedup/cap/reorder. PASS.

## 3. The eval or test passed

Done-check run fresh against the real dev server, real API, real
Postgres, real headless Chromium, driven through the actual chat UI
(conversation #394):

```
$ cd web && npm run build
> web@0.0.0 build
> tsc -b && vite build
✓ 627 modules transformed.
✓ built in 1.89s
```

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

Compose input was empty before the click, contained the exact clicked
chip's text after, and was never auto-submitted (no new message
appeared). Zero console errors. PASS.

Unit tests (`FollowUpChips.test.tsx`, `api.asAssistantContent.test.ts`
additions) written by test-writer from the brief but still cannot execute
— `web/package.json` has no test runner installed, a pre-existing gap
carried from the prior two slices, not fixed here (installing one is a
new dependency, out of this brief's scope).

## 4. The no-slop review found no unresolved issues

First pass (before this record) found one real issue: the doc comment
above `asAssistantContent()` in `api.ts` named "ChartView and SqlDetails"
as the check's consumers — stale the moment `FollowUpChips` became a
third consumer, and the same class of staleness the prior slice's own
gate had already caught and fixed once. Fixed by generalizing the comment
to "any per-message assistant component" so it can't go stale on the next
consumer either (ratchet: second occurrence of the same comment pattern).

Second pass (after the fix, full checklist re-run from scratch): no
findings. All 8 applicable categories pass clean (dead code, duplication,
naming, comments, consistency, scope, fake-done, verified-not-claimed).
One non-blocking note: no test case for an empty-string follow-up
entry — not required by the brief, not fixed. PASS.

## 5. The shipping proof is attached

Screenshots from the fresh live Playwright run above:
- `chips-before-click.png` — real assistant message with 5 real chips
  rendered beneath it, compose input empty.
- `chips-after-click.png` — same page, compose input now containing the
  exact clicked chip's text, unsent (Send button still present, no new
  message added).

Both captured against the real running app (dev server + real API +
real Postgres), not mocked.

## Rejected or changed

The stale doc comment above `asAssistantContent()` (see check 4) — caught
and fixed before this record, re-verified clean on the second no-slop
pass.

## Verdict

Accept. All five checks green; user approved with the diff and screenshots
shown above.
