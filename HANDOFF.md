# Handoff

Date: 2026-08-06
Slice just completed: plans/briefs/2026-08-06-sql-explanation-viewer.md
  + plans/logs/2026-08-06-sql-explanation-viewer.md
  (commit 865d30d)

## State of the work

- **Every assistant chat message now has a collapsed "View SQL" section**
  beneath it (alongside the existing chart and raw JSON dump), rendered by
  new `web/src/components/SqlDetails.tsx` — a native `<details>/<summary>`
  element, collapsed by default, revealing the real executed `sql` (in a
  `<pre>`, matching the existing raw-dump styling) and
  `analysis.explanation` (plain text) on click.
- **`web/src/api.ts`'s `AssistantContent`/`asAssistantContent()`** now
  also expose `sql` (top-level `content_json` key) and
  `analysis.explanation`, using the same guard-clause style already there
  for `rows`/`chart_spec` — returns `null` (renders nothing extra) for any
  message missing either, which includes every pre-`sql`-field legacy
  message already in the DB.
- **`web/src/App.tsx`'s message loop** renders both the chart and the SQL
  section through a single `AssistantResult` helper (resolves
  `asAssistantContent` once per message) — this replaces the two
  near-identical `AssistantChart`/`AssistantSql` helpers the brief
  originally suggested; the no-slop pass caught the duplication before
  commit and it was collapsed into one, re-verified with a fresh build
  and a fresh live Playwright run afterward (behavior unchanged).
- **Gate 2 all five checks green** (full record:
  `artifacts/reviews/2026-08-06-sql-explanation-viewer.md`). Two real
  no-slop findings caught and fixed: a stale comment (said the shape
  check existed only for `ChartView`'s benefit, no longer true) and the
  duplicated-helper pattern above.
- **No new dependencies.** `<details>` was chosen over a
  `useState`-driven toggle specifically because the codebase has no
  `useState` used for pure view-state anywhere yet (design note:
  `artifacts/design/2026-08-06-sql-explanation-viewer.md`).
- **No backend changes** — confirmed via `git diff --stat -- app prompts`
  being empty for this slice.

## Proof

```
$ cd web && npm run build
✓ 626 modules transformed.
✓ built in 2.00s
```

Live Playwright proof (real backend, real Postgres, real Vite dev
server, real headless Chromium, driven through the actual chat UI
against fresh conversations):

Conversation 392 — "How many orders have the status 'delivered'?" →
collapsed by default (`openBefore: false`), click reveals the real SQL
and explanation:
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

Conversation 393 — "What are the top 5 product categories by number of
orders?" → confirms the SQL section coexists correctly with a real
rendered bar chart:
```
{ "canvasCount": 1, "summaryCount": 1, "consoleErrors": [] }
```

Dev server stopped after verification, confirmed free via `netstat`.

## Open questions / known issues

- **Frontend unit tests exist but cannot execute.**
  `web/tests/api.asAssistantContent.test.ts` and
  `web/tests/SqlDetails.test.tsx` were written by the test-writer subagent
  from this slice's brief, but `web/package.json` still has no test
  runner (vitest/jest) — a pre-existing gap, not fixed this slice (adding
  one is a new dependency). Intended command once installed:
  `cd web && npx vitest run`.
- **`AssistantResult` is now the single per-message resolution point** for
  both the chart and the SQL section. The next slice (follow-up chips)
  will extend it a third time — if a *third* near-identical prop-drilling
  need shows up after that, consider whether `AssistantResult` should grow
  a proper props contract rather than accreting one-off additions.
- Carried over, unchanged from the previous handoff (still true, still
  unaddressed):
  - `chart_spec` still has no fixed schema by design (`prompts/analyze.md`);
    `ChartView.tsx`'s alias-resolution approach remains the frontend's
    answer to this.
  - ECharts auto-hides overlapping x-axis category labels under the
    `max-w-2xl` container width — not a bug, tooltip still shows full
    names, unaddressed by design.
  - No charting library styling beyond a single fixed accent color; no
    dark mode; no table-view toggle (raw `<pre>` dump covers it).
  - Decimal-valued rows still serialize as JSON strings, not numbers, in
    the raw `<pre>` dump (handled only where `ChartView.tsx`'s
    `toFiniteNumber()` already copes with it).
  - `NullPool` needs re-evaluation under uvicorn's single persistent
    event loop — still flagged in `app/db/session.py`'s own comment.
  - What happens to an already-computed answer when its persistence write
    fails: still a plain 500 / silently truncated SSE stream.
  - `plans/logs/_auto-capture.md` remains silently uncommitted across
    every commit (pre-existing workflow gap, by design of the capture
    hook's timing).
  - `tests/test_seed_idempotency.py`'s own real Postgres deadlock
    (M1-era, unrelated code) remains uninvestigated.
  - Lint/type tooling on the Python side (`ruff`, `mypy`) remains
    unaddressed.
  - A `response.content[0].text`/`ThinkingBlock` bug pattern is fixed only
    in `analyze_answer.py`; `generate_sql.py`, `repair_sql.py`,
    `describe.py` still carry the same fragile assumption.
  - The project's own `.venv` (Python 3.11.15) must be used explicitly for
    backend commands.
  - API base URL is a hardcoded `http://localhost:8000` constant in
    `web/src/api.ts`.
  - `Conversation`'s `user_id` FK to `users` is deliberately omitted —
    `users` doesn't exist yet (F8).

## Next slice (the brief, written NOW while context is hot)

Goal:
Render `analysis.follow_ups` as clickable chip buttons beneath each
assistant message; clicking a chip populates the compose input with that
follow-up's text (does not auto-submit).

Constraints:
- No new dependencies. Follow established frontend conventions: Tailwind
  utility classes inline, plain function components with
  inline-destructured typed props, local component state — same pattern
  `ChartView.tsx`/`SqlDetails.tsx` and `AssistantResult` (`App.tsx`)
  already use for per-message rendering.
- Do not auto-submit on click — the user must still be able to edit the
  populated text and press Send, same as typing it manually. Reuse
  `ConversationDetailView`'s existing `question`/`setQuestion` state
  (`App.tsx`) as the target; do not introduce a second state store for
  the compose input.
- No backend changes. Do not touch `analyze_answer.py`,
  `prompts/analyze.md`, `AnalyzeResponse`, or any endpoint in
  `app/main.py`.
- Render exactly what `analysis.follow_ups` contains — no deduplication,
  no capping the number shown, no reordering.

Inputs:
- `web/src/api.ts`'s `Analysis` interface already declares
  `follow_ups: string[]`; `AssistantContent`/`asAssistantContent()` need
  it added the same way `sql`/`explanation` were added this slice (same
  guard-clause style — `Array.isArray`, consistent with the existing
  `rows` check's looseness on element validation).
- `web/src/components/SqlDetails.tsx` and `App.tsx`'s `AssistantResult`
  helper as the established per-message-component pattern — note
  `AssistantResult` currently only takes `{ message }`; this slice will
  need it (or a caller one level up) to also receive a callback into
  `ConversationDetailView`'s `setQuestion`, since chip clicks must reach
  state that currently lives one component above `AssistantResult`.
- A real assistant message's `analysis.follow_ups` array (this handoff's
  own Proof above shows real question text if re-run; any row in
  `app.messages` has real examples) as ground truth for what's actually
  available to render.

Outputs:
- `web/src/api.ts`: `AssistantContent` gains `followUps: string[]`.
- New `web/src/components/FollowUpChips.tsx` (or equivalent): renders one
  button per follow-up string; `onSelect(text: string)` prop fires on
  click.
- `web/src/App.tsx`: `AssistantResult` (or its caller) wires
  `FollowUpChips`'s `onSelect` through to `ConversationDetailView`'s
  `setQuestion`.

Done-check:
Start the dev server (`docker compose up` or `npm run dev` + the API),
ask a real question through the chat UI, screenshot the chips rendered
with real follow-up text beneath the message, click one, screenshot the
compose input now populated with that exact text (not yet sent).

Out-of-scope:
- Auto-submitting a follow-up on click.
- Any change to `SqlDetails.tsx` or `ChartView.tsx`.
- Any backend change.
- Deduplicating, capping, or reordering the follow-ups list.
