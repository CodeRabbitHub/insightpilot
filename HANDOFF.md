# Handoff

Date: 2026-08-06
Slice just completed: plans/briefs/2026-08-06-chart-view.md
  + plans/logs/2026-08-06-chart-view.md
  (commits ac7791a, add6707)

## State of the work

- **The chat UI renders a real ECharts bar chart beneath chartable
  assistant messages.** New `web/src/components/ChartView.tsx` takes
  `chartSpec`/`rows` and renders one bar chart, or `null`, based purely
  on whether the shape resolves to a recognized bar chart — never a
  guessed axis, never an error for anything else.
- **`chart_spec` resolution is now known to need at least these real
  key-name aliases** (all confirmed against live, already-persisted
  data, not hypothetical): type discriminator as `chart_type` OR `type`,
  checked against exactly `'bar'`; x-field as `x` OR `x_field`; y-field
  as `y` OR `y_field`. Everything that doesn't resolve renders nothing —
  this includes two more real non-bar shapes seen this session on top of
  the ones named in the brief: `{"chart_type":"none","reason":...}` and,
  newly observed during this slice's own gate run, `{"type":"scalar",
  "value":96478,"value_field":"delivered_order_count"}`. The component
  handled the scalar shape correctly without ever needing to recognize
  `"scalar"` specifically — the strict `=== 'bar'` check is what made
  that safe.
- **`web/src/api.ts` gained `Analysis`, `ConversationMessageResult.
  analysis`, and `asAssistantContent()`** — a small runtime shape-check
  that returns `{rows, chartSpec}` or `null` given a message's
  `content_json`, since `content_json` still holds either a user
  question or an assistant answer and can't be typed narrower at the
  field level. Confirmed it degrades safely for the pre-`analysis`-field
  legacy messages already in the DB (`typeof analysis !== 'object'`
  catches `undefined`, returns `null`, renders nothing extra for them).
- **`web/src/App.tsx`'s message loop** now renders a new `AssistantChart`
  helper alongside (not replacing) the existing raw JSON `<pre>` dump,
  for `role === 'assistant'` messages only.
- **Gate 2 all five checks green** (full record:
  `artifacts/reviews/2026-08-06-chart-view.md`). One real no-slop finding
  caught and fixed: the initial draft only checked `chart_type`, missing
  a real `type`-keyed bar variant already sitting in the live DB
  (message id 462) for this brief's own done-check question — found by
  directly querying the DB, not just trusting a claim. Fixed by
  resolving the type discriminator the same alias-first way the x/y
  field names already were.
- **Dependencies**: `echarts` + `echarts-for-react` added to
  `web/package.json` (pre-approved, named in ARCHITECT.md's stack) — the
  first new frontend dependencies since the scaffold.
- **First `web/src/components/` file.** No routing library, no
  shadcn/ui, no dark mode added — all still deferred, same as every
  prior frontend slice.
- **The "View SQL"/explanation section and follow-up chips are still
  untouched** — `analysis.explanation`, `analysis.follow_ups`, and `sql`
  are all already present in every real `content_json` this slice's own
  proof observed, just not rendered anywhere yet. This is exactly the
  next slice (below).

## Proof

```
$ cd web && npm run build
> web@0.0.0 build
> tsc -b && vite build
vite v8.2.0 building client environment for production...
transforming...✓ 625 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                     0.46 kB │ gzip:   0.29 kB
dist/assets/index-D7gtQICa.js   1,282.56 kB │ gzip: 425.02 kB
✓ built in 4.79s
```

Live shipping proof (real backend, real Postgres + Anthropic, real Vite
dev server, real headless Chromium via Playwright, driven through the
actual chat UI against a fresh conversation, `POST /api/conversations` →
id 391):

"What are the top 5 product categories by number of orders?" →
`chart_spec: {"x":"product_category_name","y":"order_count",
"chart_type":"bar","orientation":"vertical","title":"Top 5 Product
Categories by Number of Orders"}` → a correctly rendered 5-bar chart
(all real category names and counts), screenshot captured.

"How many orders have the status 'delivered'?" (same conversation) →
`chart_spec: {"type":"scalar","value":96478,
"value_field":"delivered_order_count"}` → no chart rendered:
```
{
  "canvasCountAfterFirst": 1,
  "canvasCountAfterSecond": 1,
  "consoleErrors": []
}
```
Zero browser console errors across both questions. Vite dev server
(port 5173) stopped after verification, confirmed free via `netstat`.

## Open questions / known issues

- **`chart_spec` has at least 4 real observed shapes now** (see State of
  the work above) — still no fixed schema by design
  (`prompts/analyze.md`), and tightening it there remains explicitly
  deferred, same as the previous handoff's decision. `ChartView.tsx`'s
  alias-resolution approach is the frontend's answer to this for now;
  if a *second* logged correction of the "LLM picks a different JSON key
  for the same discriminator" pattern shows up in a future slice (this
  session's `chart_type`/`type` fix was the first), promote a standing
  rule to CLAUDE.md/no-slop.md per the ratchet.
- **ECharts auto-hides overlapping x-axis category labels** when there
  isn't enough width for all of them (observed: only 3 of 5 category
  labels shown for the 5-category proof chart, in the ~672px-wide
  `max-w-2xl` container) — this is ECharts' own default `axisLabel`
  interval behavior, not a bug, and the tooltip still shows the full
  category name on hover. Not addressed this slice; revisit only if a
  future slice needs every label always visible (e.g. rotating labels or
  widening the container).
- **No charting library styling beyond a single fixed accent color and
  the dataviz skill's minimum bar/gridline/tooltip spec** — no legend
  (correct, single series), no dark mode (nothing else in this app has
  one yet), no table-view toggle (the existing raw `<pre>` dump already
  covers that fallback). All deliberate, documented in
  `artifacts/design/2026-08-06-chart-view.md`.
- **`web/src/App.tsx` has no per-field message rendering for
  `sql`/`explanation`/`follow_ups` yet** — only the raw `<pre>` dump and,
  as of this slice, the chart. The next slice (below) starts on this.
- Carried over, unchanged from the previous handoff (still true, still
  unaddressed):
  - Decimal-valued rows still serialize as JSON strings, not numbers —
    `ChartView.tsx`'s `toFiniteNumber()` already copes with this for
    y-values, but it remains true elsewhere (e.g. the raw `<pre>` dump).
  - `NullPool` needs re-evaluation under uvicorn's single persistent
    event loop — still flagged in `app/db/session.py`'s own comment.
  - What happens to an already-computed answer when its persistence
    write fails: still a plain 500 / silently truncated SSE stream.
  - `plans/logs/_auto-capture.md` remains silently uncommitted across
    every commit (pre-existing workflow gap, by design of the capture
    hook's timing).
  - `tests/test_seed_idempotency.py`'s own real Postgres deadlock
    (M1-era, unrelated code) remains uninvestigated.
  - Lint/type tooling on the Python side (`ruff`, `mypy`) remains
    unaddressed.
  - A `response.content[0].text`/`ThinkingBlock` bug pattern is fixed
    only in `analyze_answer.py`; `generate_sql.py`, `repair_sql.py`,
    `describe.py` still carry the same fragile assumption. Still only
    one documented fixed occurrence; promote a shared
    `extract_response_text()` helper if it recurs.
  - The project's own `.venv` (Python 3.11.15) must be used explicitly
    for backend commands.
  - No frontend test runner exists — live CDP/Playwright verification
    stands in for it at Gate 2, for frontend-touching slices only.
  - API base URL is a hardcoded `http://localhost:8000` constant in
    `web/src/api.ts`.
  - `Conversation`'s `user_id` FK to `users` is deliberately omitted —
    `users` doesn't exist yet (F8).

## Next slice (the brief, written NOW while context is hot)

Goal:
Render `analysis.explanation` and the executed `sql` in a collapsed
"View SQL" section beneath each assistant message, expandable on click,
using data already flowing through `content_json` (no backend change).

Constraints:
- Follow-up chips are a separate, later slice (see Out-of-scope) — this
  slice is exactly the SQL/explanation section, one outcome.
- No new dependencies. Follow established frontend conventions: Tailwind
  utility classes inline, plain function components with
  inline-destructured typed props, local component state (no new
  state-management library) — same pattern `ChartView.tsx` and
  `AssistantChart` already use for per-message rendering.
- Reuse `asAssistantContent()` (`web/src/api.ts`) for the runtime shape
  check rather than re-deriving one; it currently returns `{rows,
  chartSpec}` and will need `sql`/`explanation` added to its return
  shape (or a second small accessor) since those are the two new fields
  this slice needs from `content_json`.
- Collapsed by default; a click reveals both the SQL (in a `<pre>`,
  monospace, matching the existing raw-dump styling already used
  elsewhere in `App.tsx`) and `analysis.explanation` as plain text.
- No backend changes. Do not touch `analyze_answer.py`,
  `prompts/analyze.md`, `AnalyzeResponse`, or any endpoint in
  `app/main.py`.

Inputs:
- `web/src/api.ts`'s `asAssistantContent()` and `Analysis` interface
  (`{summary, explanation, chart_spec, follow_ups}`) — the exact fields
  already available per message, just not yet rendered beyond
  `chart_spec`.
- `web/src/components/ChartView.tsx` and `web/src/App.tsx`'s
  `AssistantChart` helper (`App.tsx`, near the message-rendering loop)
  as the established pattern for a small per-message component gated on
  `role === 'assistant'`.
- A real assistant message's full shape (this handoff's own Proof above,
  or any row in `app.messages` — e.g. `sql: "SELECT ..."`,
  `analysis.explanation: "The query joined..."`) as ground truth for
  what's actually available to render.

Outputs:
- `web/src/api.ts`: `asAssistantContent()` (or a small sibling accessor)
  exposes `sql` and `analysis.explanation` alongside the existing
  `rows`/`chartSpec`.
- New `web/src/components/SqlDetails.tsx` (or equivalent): a collapsed-
  by-default `<details>`/toggle-button section showing the SQL and
  explanation for one assistant message.
- `web/src/App.tsx`'s message loop renders it alongside `ChartView` and
  the existing raw JSON dump — nothing removed.

Done-check:
Start the dev server (`docker compose up` or `npm run dev` + the API),
ask a real question through the chat UI, screenshot (via Playwright,
same as this slice) the message showing the section collapsed by
default, then click to expand it and screenshot showing the real SQL
and explanation text revealed.

Out-of-scope:
- Follow-up chips (`analysis.follow_ups` rendered as clickable buttons
  that populate the compose input) — separate next-next slice.
- Any chart-rendering change (`ChartView.tsx` stays as-is).
- Any backend change.
- Syntax highlighting for the SQL — plain `<pre>` text is enough for
  this slice, matching the existing raw-dump convention.
