# Slice log — dashboard-strictmode-fetch-guard

Date: 2026-08-08
Brief: plans/briefs/2026-08-08-dashboard-strictmode-fetch-guard.md

## The plan you approved

Add a local `stale` flag (originally proposed as `ignore`, per the
brief's Constraints citing React's own docs) to `DashboardView.tsx`'s
mount `useEffect`: `false` at the start of each invocation, checked
before each of `setDashboard`/`setError`/`setLoading` in
`.then`/`.catch`/`.finally`, flipped `true` in the effect's cleanup. No
`AbortController`, no other part of the file touched. No design note —
purely internal race fix, zero visible behavior change on the normal
path.

## The diff you accepted

Commit `b0ab678` — "Guard DashboardView's mount fetch against
StrictMode's stale double-invoke":
```
 .../2026-08-08-dashboard-strictmode-fetch-guard.md | 136 +++++++++++++++
 .../2026-08-08-dashboard-strictmode-fetch-guard.md |  89 ++++++++++
 plans/logs/_auto-capture.md                        |  21 +++
 web/src/components/DashboardView.tsx               |  16 +-
 web/tests/DashboardView.test.tsx                   | 183 +++++++++++++++++++++
 5 files changed, 442 insertions(+), 3 deletions(-)
```
(A separate catch-up commit, `982f6d7` — "Handoff: drag-reposition slice
done, next brief is strictmode-fetch-guard" — closed out a handoff commit
skipped at the end of the prior session; not new work product of this
slice.)

## The done-check output

```
$ cd web && npm run build
> web@0.0.0 build
> tsc -b && vite build

vite v8.2.0 building client environment for production...
✓ 628 modules transformed.
✓ built in 856ms
```

Real-server shipping proof, pre-fix repro (code temporarily reverted via
`git stash` to confirm the bug is real before trusting the fix) —
Playwright dragging "Race proof Second" onto "Race proof First"'s slot
immediately after page load, no settle-wait:
```json
{
  "headingsBeforeDrag": ["Race proof First", "Race proof Second"],
  "headingsRightAfterDrop": ["Race proof Second", "Race proof First"],
  "headingsAfter6sWait": ["Race proof First", "Race proof Second"],
  "consoleErrors": []
}
```
Reorder visibly reverts after ~6s — bug reproduced.

Post-fix confirmation, same script, final code, fresh proof cards:
```json
{
  "headingsBeforeDrag": ["Race proof First", "Race proof Second"],
  "headingsRightAfterDrop": ["Race proof Second", "Race proof First"],
  "headingsAfter6sWait": ["Race proof Second", "Race proof First"],
  "consoleErrors": []
}
```
Reorder survives the full 6-second wait — no revert, zero console errors.
Proof cards deleted afterward each round; dashboard 1 reconfirmed back to
its baseline 7 pre-existing cards both times.

Full check detail: `artifacts/reviews/2026-08-08-dashboard-strictmode-fetch-guard.md`.

## One thing you rejected or changed

Headline judgment call: the shipped flag is named `stale`, not `ignore`
as the brief's Constraints literally specified (citing React's own
"Fetching data with Effects" docs). The no-slop review's first pass
caught that this exact guard pattern already exists in `App.tsx`'s
conversation-detail effect, using the name `stale` — shipping `ignore`
would have left the same concept named two different ways in the same
codebase. Renamed to `stale` for cross-file vocabulary consistency,
overriding the brief's literal wording; presented to and accepted by the
user at Gate 2. First occurrence of this specific finding shape (a brief
citing external docs' naming over the codebase's own established
vocabulary) — not yet a repeat, so no CLAUDE.md/no-slop.md promotion this
slice; watch for a second occurrence.

Three smaller no-slop fixes alongside it, all mechanical:
- Reverted an incidental, unrelated reword of a pre-existing test comment
  (about the Rename button's card-merge semantics) that had been smuggled
  into `web/tests/DashboardView.test.tsx` by the test-writer agent —
  confirmed reverted byte-for-byte against commit `1cc5574`.
- The original two race tests only proved the `.then`/`.catch` guards
  (both only exercised the ordering where the stale call settles *after*
  the fresh one, where an unguarded `finally` would be visually
  indistinguishable). Added a third test resolving the stale call
  *before* the fresh one, while the fresh call is still pending, to
  actually prove the `setLoading` guard matters.
- A test-file header comment narrated the session's TDD sequencing
  ("written BEFORE the fix lands... expected to fail against the current
  pre-fix effect body") rather than describing current behavior — reworded
  to present tense so it isn't stale-on-arrival once merged.

## The next smallest slice

`App.tsx`'s conversations-list mount effect (`web/src/App.tsx:164-171`)
has the identical unguarded StrictMode double-invoke race this slice just
fixed in `DashboardView.tsx` — same missing guard, same fix shape (the
`stale`-flag pattern, already proven correct twice in this codebase:
`App.tsx`'s own conversation-detail effect, and now `DashboardView.tsx`).
