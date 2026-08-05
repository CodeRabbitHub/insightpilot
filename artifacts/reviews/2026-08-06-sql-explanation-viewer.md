# Review gate — sql-explanation-viewer

Date: 2026-08-06
Brief: plans/briefs/2026-08-06-sql-explanation-viewer.md
Diff reviewed: working tree (uncommitted) —
`web/src/api.ts`, `web/src/App.tsx`, new `web/src/components/SqlDetails.tsx`,
new `web/tests/api.asAssistantContent.test.ts`, new
`web/tests/SqlDetails.test.tsx`, new
`artifacts/design/2026-08-06-sql-explanation-viewer.md`,
new `plans/briefs/2026-08-06-sql-explanation-viewer.md`.

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review

```
$ git diff --stat
 web/src/App.tsx | 12 ++++++++---
 web/src/api.ts  | 10 +++++++++-
 2 files changed, 18 insertions(+), 4 deletions(-)
```
Plus 3 new files (`SqlDetails.tsx`, 19 lines; two test files, 237 lines
combined) and one new design note. Small, entirely readable line by line.
Pass.

(`plans/logs/_auto-capture.md` shows modified in `git status` but that's
the pre-existing, unrelated auto-capture-hook gap already carried in
every previous handoff — not part of this diff.)

## 2. The stated goal matches the actual change

Brief's Goal: render `analysis.explanation` and the executed `sql` in a
collapsed "View SQL" section beneath each assistant message, expandable
on click, using data already flowing through `content_json` (no backend
change).

What the diff does: `asAssistantContent()` (`web/src/api.ts`) now also
extracts `sql` (top-level `content_json` key) and `analysis.explanation`,
returning `null` if either is missing or the wrong type — same
guard-clause style as the existing `rows`/`chart_spec` checks. New
`SqlDetails.tsx` renders a `<details>/<summary>` labeled "View SQL",
collapsed by default, revealing the SQL in a `<pre>` and the explanation
as plain text on click. `App.tsx` renders it via a small helper
(`AssistantResult`, see below) gated on `role === 'assistant'`, alongside
the untouched chart and raw JSON dump. No backend file touched (`git diff
--stat -- app prompts` is empty). Matches the goal exactly — no missing
piece, nothing extra.

One deliberate deviation from the brief's literal wording, not a scope
violation: the brief allowed adding a `AssistantSql` helper "mirroring
`AssistantChart`" as a separate sibling. The no-slop pass (below) flagged
that as the start of a duplicated pattern, so it was collapsed into a
single `AssistantResult` helper that resolves `asAssistantContent` once
and renders both the chart and the SQL section. Behavior is identical;
this is a simplification within the brief's own stated outputs, not an
added feature. Pass.

## 3. The eval or test passed

No backend/LLM behavior changed, so no eval run needed. The brief's own
done-check was run fresh, twice (once before a no-slop-driven refactor,
once after, to confirm the refactor didn't change behavior):

```
$ cd web && npm run build
> web@0.0.0 build
> tsc -b && vite build
✓ 626 modules transformed.
dist/assets/index-CdrB4LcF.js   1,283.19 kB │ gzip: 425.17 kB
✓ built in 2.00s
```

Live Playwright run against the real dev server + real API (conversation
id 394, post-refactor):
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
`openBefore: false` confirms collapsed-by-default; `openAfter: true` plus
the real `sqlText`/`explanationText` confirm the click reveals the real
values. Zero console errors. Pass.

Frontend unit tests (`web/tests/api.asAssistantContent.test.ts`,
`web/tests/SqlDetails.test.tsx`) were written by the test-writer subagent
from the brief before implementation, but **cannot execute** — no test
runner (vitest/jest) is installed in `web/package.json`, a pre-existing
gap this slice's brief didn't ask to fix (adding one is a new dependency,
forbidden without asking). Carried forward as an open issue, same as
every prior frontend slice's handoff.

## 4. The no-slop review found no unresolved issues

no-slop-reviewer subagent findings and resolution:

1. **Stale comment** (`web/src/api.ts`, above `asAssistantContent`) — said
   the function existed only for `ChartView`'s benefit; no longer true
   now that `SqlDetails` also depends on it. **Fixed**: comment now names
   both consumers.
2. **Duplication** — `AssistantChart`/`AssistantSql` were two
   near-identical helpers each independently re-resolving
   `asAssistantContent` for the same message; flagged as the start of a
   copy-paste pattern the very next slice (follow-up chips) would make a
   third instance of. **Fixed**: collapsed into one `AssistantResult`
   helper that resolves once and renders both `ChartView` and
   `SqlDetails`. Re-verified with a fresh build and a fresh live
   Playwright run after the change (both above) — behavior unchanged.
3. Flagged the tests' inability to execute (no runner installed) —
   **accepted exception**, written into each test file's header, matches
   the project's pre-existing, previously-documented gap.
4. Flagged the `<details>` decision and the no-syntax-highlighting
   omission — both **accepted**, backed by the design note's rejected
   alternative and the brief's own out-of-scope line respectively.

No unresolved findings remain. Pass.

## 5. The shipping proof is attached

Real backend (Postgres + already-running FastAPI on :8000, unrelated to
this session) + real Vite dev server (:5173) + real headless Chromium via
Playwright (already installed from the previous slice's session; reused,
nothing new added to `package.json`), driven through the actual chat UI
against fresh conversations, not called directly.

**Conversation 392** — "How many orders have the status 'delivered'?":
section rendered collapsed by default (screenshot: only "▶ View SQL"
visible, chart correctly absent since `chart_spec.chart_type ==
"single_value"`); clicking it revealed the real SQL
(`SELECT COUNT(*) AS delivered_order_count FROM olist.orders WHERE
order_status = 'delivered'`) and the real explanation text. Both states
screenshotted.

**Conversation 393** — "What are the top 5 product categories by number
of orders?": confirms the SQL section coexists correctly with a real
rendered bar chart (`canvasCount: 1`, `summaryCount: 1`, zero console
errors) — this question exercises the same per-message block
(`AssistantResult`) this slice's refactor touched, so it's a direct
regression check on `ChartView`'s untouched rendering path.

**Conversation 394** (post-refactor re-run) — same 'delivered' question,
confirms `AssistantResult`'s collapsed→expanded behavior is unchanged
after collapsing the two helpers into one (full JSON output above, check
3).

Dev server stopped after verification, confirmed free via `netstat`.
Screenshots captured to the session scratchpad (not committed — this
repo doesn't commit proof screenshots, per the chart-view slice's own
precedent of describing rather than committing them).

## Rejected or changed

Changed: the brief's suggested `AssistantSql` sibling helper was rejected
in favor of a single `AssistantResult` helper that resolves
`asAssistantContent` once for both the chart and the SQL section — a
no-slop-driven simplification caught before commit, not smuggled in
un-reviewed. This is the "at least one thing" this gate record names.

## Verdict

**Accept.** All five checks green.
