# Brief — chart-view

Date: 2026-08-06
Milestone: M5 Chat UI (chart + SQL viewer + follow-up chips)

Goal:
Render `analysis.chart_spec` as a real ECharts bar chart beneath each
assistant message in the chat UI, when the data is chartable, using the
real `chart_spec`/`rows` data that already flows through
`/api/conversations/{id}/messages`.

Constraints:
- New frontend dependencies, pre-approved (ARCHITECT.md names Apache
  ECharts as the frontend stack; this session approved `echarts` +
  `echarts-for-react` specifically, the React wrapper, to avoid
  hand-rolling imperative lifecycle/resize management). No other new
  dependency without asking again.
- `chart_spec` has NO fixed schema (confirmed from real observed output,
  see HANDOFF.md's Open questions) — real shapes vary (`x`/`y` vs
  `x_field`/`y_field`; a non-chartable result as either
  `{"chart_type": "none", ...}` or a plain `{}`). The chart component
  must be defensive: treat any `chart_spec` that doesn't resolve to a
  recognized `chart_type` (start with `"bar"` only — the only type
  observed in real output so far) AND a resolvable x-field/y-field pair
  present in `rows`' own keys as "not chartable" and render nothing
  chart-related for that message (no error, no placeholder chart) —
  never guess or fabricate axes from a malformed spec.
- Do NOT touch `analyze_answer.py`, `prompts/analyze.md`, or
  `AnalyzeResponse` — tightening `chart_spec`'s schema is a separate
  future slice (this session's decision).
- Follow established frontend conventions: Tailwind utility classes
  inline (no CSS modules/stylesheets), plain function components with
  inline-destructured typed props, no new state-management library.
- No backend changes.

Inputs:
- `web/src/App.tsx` lines 92-103 (`ConversationDetailView`'s message
  rendering loop — the only place assistant content renders today) and
  its surrounding `stale`-flag async-guard pattern.
- `web/src/api.ts` (full file) — `MessageDetail.content_json:
  Record<string, unknown>`, `ConversationMessageResult` (currently
  missing `analysis` entirely, stale relative to the backend),
  `fetchConversation()`/`postConversationMessage()`.
- `app/pipeline/analyze_answer.py`'s `AnalyzeResponse` (`chart_spec:
  dict[str, Any]`, no further validation) and `prompts/analyze.md` (no
  fixed chart_spec schema) — read-only reference for what shapes are
  actually possible, not to be modified.
- Real observed `chart_spec` examples (use as fixtures):
  `{"chart_type":"none","reason":"..."}` for a scalar result
  (2026-08-05 handoff's live HTTP proof), and
  `{'chart_type': 'bar', 'x': 'product_category_name', 'y': 'order_count',
  'orientation': 'vertical', 'title': '...'}` for a groupable result
  (wire-analyze-answer slice's proof).
- PRD.md's frontend stack section and M5's milestone description for
  scope boundaries.

Outputs:
- `web/package.json` gains `echarts` + `echarts-for-react`.
- `web/src/api.ts`: `ConversationMessageResult` (and any shared
  `Analysis`-shaped interface used by both it and message rendering)
  gains an `analysis` field matching the backend's real shape.
- New `web/src/components/ChartView.tsx`: given a message's parsed
  `analysis`/`rows`, renders an ECharts bar chart when `chart_spec`/`rows`
  resolve to a recognized, chartable shape; renders nothing otherwise.
- `web/src/App.tsx`'s message-rendering loop uses the new component
  alongside (not replacing) the existing raw JSON `<pre>` dump — the
  "View SQL"/explanation section and follow-up chips remain later
  slices' work.

Done-check:
Start the dev server (`docker compose up` or `npm run dev` + the API),
ask a real chartable question ("What are the top 5 product categories by
number of orders?") through the chat UI, and screenshot (via CDP) the
message showing a real rendered bar chart beneath it — then ask a real
non-chartable scalar question ("How many orders have the status
'delivered'?") and screenshot showing no chart renders (no error, no
empty chart box) for that message.

Out-of-scope:
- Any chart type other than bar (line/pie/table) — add when real output
  actually produces one; speculative support for unobserved shapes is not
  this slice's job.
- Tightening `chart_spec`'s schema in `prompts/analyze.md`/
  `AnalyzeResponse` — deferred, this session's explicit decision.
- The "View SQL"/explanation collapsed section and follow-up chips —
  separate M5 slices.
- Any backend change.
- Pinning charts to a dashboard (M6).
