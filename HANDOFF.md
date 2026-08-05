# Handoff

Date: 2026-08-05
Slice just completed: plans/briefs/2026-08-05-wire-analyze-answer.md
  + plans/logs/2026-08-05-wire-analyze-answer.md
  (commits 8d1f60e, 745a797, e9f5278)

## State of the work

- **The backend text-to-SQL pipeline now returns real analysis data
  end-to-end, on every request path.** `app/pipeline/answer.py`'s
  `get_answer(question)` calls `analyze_answer(question, sql, rows)`
  itself, internally, right after a successful validate+execute, and
  returns `(sql, rows, analysis)` — a real `AnalyzeResponse` instance,
  not a placeholder. A failure there propagates uncaught, same as an
  unrepaired validate/execute failure (no partial/degraded response).
- **`app/main.py`'s `AskResponse` and `ConversationMessageResult` each
  carry a nested `analysis: AnalyzeResponse` field**, reusing the real
  model directly (never hand-flattened). All three endpoints (`/api/ask`,
  `/api/ask/stream`, `/api/conversations/{id}/messages`) forward it;
  `_persist_exchange()`/`_persist_message_pair()` needed no code change
  (`jsonable_encoder(response)` already covers new fields), so persisted
  message `content_json` carries `analysis` automatically too. Verified
  live: a real `uvicorn` server hit with a real `curl POST /api/ask`
  returned `analysis` alongside `sql`/`rows` in the actual HTTP response
  (see Proof).
- **Every existing call site of the old 2-tuple return, and every
  hardcoded `{"sql","rows"}`-only shape assertion, updated to match** —
  `evals/run.py`, `verify_answer.py`, `verify_analyze_answer.py` (which
  also stopped calling `analyze_answer()` a second, redundant time — a
  no-slop finding, fixed to reuse `get_answer()`'s own result),
  `tests/test_question_parameter.py`, `tests/test_analyze_answer.py`,
  and the exact-key-set assertions in `tests/test_api_ask.py`,
  `tests/test_api_ask_stream.py`, `tests/test_api_conversations.py`,
  `tests/test_api_conversations_read.py`.
- **Gate 2 all five checks green** (full record:
  `artifacts/reviews/2026-08-05-wire-analyze-answer.md`), one real
  no-slop finding caught and fixed (the redundant `analyze_answer()`
  call above).
- **Promoted a second-occurrence race to a structural fix.** This
  slice's new mandatory Anthropic call pushed real full-suite runtime
  from ~250s to ~570-840s. Twice this session, a manual full-suite
  verification run raced `.claude/hooks/stop_verify.py`'s own automatic
  run against the same live Postgres DB, corrupting shared rows
  mid-test (`app.catalog_tables.customers`'s description,
  `app.kb_chunks`) — the exact race the 2026-08-03 repair-loop slice had
  already hit once and only documented, not fixed. Per the ratchet rule,
  fixed at the mechanism level this time: `stop_verify.py`'s subprocess
  timeout raised 600s -> 1200s, plus a real file lock
  (`.claude/.suite_lock`, gitignored, stale-reclaimed after 1300s) so two
  full-suite runs can never touch the DB at once again. Lock
  acquire/release/stale-reclaim behavior smoke-tested in isolation;
  DB confirmed clean (zero corrupted descriptions, `kb_chunks` at its
  correct count of 16) after a subsequent clean, uncontested full run
  (329/329, 788s).
- **Frontend untouched** — `web/src/App.tsx` still only pretty-prints
  each message's raw `content_json` in a `<pre>`; no chart, no SQL
  viewer, no follow-up chips yet. This is expected: out of scope for
  this slice, and is exactly what the next slice (below) starts on.

## Proof

```
$ .venv/Scripts/python.exe -m app.pipeline.verify_answer
SQL:
SELECT p.product_category_name, COUNT(DISTINCT oi.order_id) AS order_count FROM olist.order_items oi JOIN olist.products p ON oi.product_id = p.product_id GROUP BY p.product_category_name ORDER BY order_count DESC LIMIT 5

Rows:
{'product_category_name': 'cama_mesa_banho', 'order_count': 9417}
{'product_category_name': 'beleza_saude', 'order_count': 8836}
{'product_category_name': 'esporte_lazer', 'order_count': 7720}
{'product_category_name': 'informatica_acessorios', 'order_count': 6689}
{'product_category_name': 'moveis_decoracao', 'order_count': 6449}

Summary:
The top 5 product categories by number of orders are cama_mesa_banho (9,417), beleza_saude (8,836), esporte_lazer (7,720), informatica_acessorios (6,689), and moveis_decoracao (6,449).

Explanation:
The query joined order_items with products on product_id, grouped by product_category_name, and counted distinct order_ids per category, then sorted descending and limited to 5 rows. The result shows cama_mesa_banho (bed/table/bath) as the leading category with 9,417 orders, followed closely by beleza_saude (health/beauty) and esporte_lazer (sports/leisure), with informatica_acessorios and moveis_decoracao rounding out the top 5.

Chart spec:
{'chart_type': 'bar', 'x': 'product_category_name', 'y': 'order_count', 'orientation': 'vertical', 'title': 'Top 5 Product Categories by Order Count'}

Follow-ups:
['What are the bottom 5 product categories by number of orders?', 'How do these top categories compare in total revenue rather than order count?', 'What is the average order value for each of these top 5 categories?', 'How have orders in these top categories trended over time?', 'What are the top product categories by number of distinct customers?']

verify_answer: PASSED

$ .venv/Scripts/python.exe -m evals.run
[PASS] What are the top 5 product categories by number of orders?
[PASS] Which payment type is used the most, by number of payments?
[PASS] Which customer state has the most customers?
[PASS] How many orders have the status 'delivered'?
[PASS] What is the average review score across all reviews?
[PASS] What is the average order value?
6/6 correct

$ .venv/Scripts/python.exe -m unittest discover tests
Ran 329 tests in 788.387s

OK
EXIT_CODE=0
```

Live HTTP shipping proof (real `uvicorn` + real `curl`, not a test):
```
$ curl -s -X POST http://127.0.0.1:8000/api/ask -H "Content-Type: application/json" \
    -d '{"question": "What is the average review score across all reviews?"}'
{"sql":"SELECT AVG(review_score) AS average_review_score FROM olist.order_reviews","rows":[{"average_review_score":"4.0864206240425703"}],"analysis":{"summary":"The average review score across all reviews is approximately 4.09 out of 5.","explanation":"The query computed the overall average of the review_score column across every row in olist.order_reviews, returning a single scalar value of about 4.0864, indicating that customers generally rate their orders quite favorably.","chart_spec":{"chart_type":"none","reason":"Single scalar value with no categorical or time dimension to plot; best displayed as a KPI/metric card rather than a chart."},"follow_ups":["What is the distribution of review scores (count of 1-star, 2-star, etc.)?","How does average review score vary by month or year?","Which product categories have the highest and lowest average review scores?","Is there a correlation between delivery time and review score?","Which sellers have the lowest average review scores?"]}}
HTTP_STATUS=200
```

## Open questions / known issues

- **`chart_spec` has NO fixed schema, confirmed from real observed
  output** — `prompts/analyze.md` only asks for "a JSON object proposing
  a reasonable chart type and axis/field mapping... No fixed schema is
  required beyond being a JSON object," and `AnalyzeResponse.chart_spec`
  is validated only as `dict[str, Any]`. Real output has used `x`/`y`
  (this handoff's own Proof above) in one run and `x_field`/`y_field` in
  an earlier run (see the analyze-answer slice's own proof), plus either
  `{"chart_type": "none", "reason": ...}` OR a plain empty `{}` for the
  non-chartable scalar case — both observed for the exact same fixed
  question across different runs. The next slice (below) is scoped to
  defend against this variance in the frontend rather than fix it at the
  source; tightening `prompts/analyze.md` + `AnalyzeResponse` to a
  documented, stricter shape (with an eval case) remains open, deferred
  to a future slice by explicit user decision this session.
- **No charting library exists in the frontend yet**
  (`web/package.json`'s only deps are `react`/`react-dom`) — the next
  slice adds `echarts` + `echarts-for-react`, the first new frontend
  dependency since the scaffold, approved by explicit user decision this
  session (PRD.md's frontend stack already named Apache ECharts).
- **`web/src/App.tsx` has no per-field message rendering yet** — the
  only rendering today is `JSON.stringify(m.content_json, null, 2)`
  inside a `<pre>` (line ~99). No `components/` directory exists yet
  either; the chart slice is a reasonable first split into its own file.
- **`get_answer()`'s LLM-call cost is now permanently ~2x** (two Voyage
  embeds + 1-2 Anthropic calls for SQL + repair, plus one more
  unconditional Anthropic call for analysis) — accepted and shipped this
  slice, but worth continuing to watch in `evals.run`'s wall-clock time
  and any future latency-budget work (PRD's p50 < 8s / p95 < 15s targets,
  M7).
- **The Stop hook's full-suite subprocess timeout is now 1200s** (was
  600s) and it holds a file lock (`.claude/.suite_lock`) around its own
  run — fixes the concurrency-corruption race documented above. Not yet
  battle-tested across many future sessions; if a THIRD occurrence of any
  DB-row-corruption symptom shows up despite the lock, treat that as a
  bug in the lock itself (e.g. a lock-file path assumption that doesn't
  hold under a different working directory), not a reason to re-loosen
  the timeout.
- **A `response.content[0].text`/`ThinkingBlock` bug pattern** — fixed
  only in `analyze_answer.py` (2026-08-05 slice); `generate_sql.py`,
  `repair_sql.py`, `describe.py` still carry the same fragile assumption.
  Still only one documented occurrence outside the fixed file; promote a
  shared `extract_response_text()` helper if it recurs.
- **The project's own `.venv` (Python 3.11.15) must be used explicitly**
  for `uvicorn`/backend commands — a bare `python`/`uvicorn` on PATH has
  resolved to an unrelated environment in a past session.
- **No frontend test runner exists** — live browser verification (via
  CDP, since chromium-cli/Playwright are unavailable here) stands in for
  it at Gate 2, for frontend-touching slices only. The next slice touches
  the frontend, so this applies.
- **API base URL is a hardcoded `http://localhost:8000` constant** in
  `web/src/api.ts` — open design debt, revisit only if a later slice
  needs configurable environments.
- **What happens to an already-computed answer when its persistence
  write fails**: unchanged, still a plain 500 for `/api/ask`, a silently
  truncated SSE stream for `/api/ask/stream` and
  `/api/conversations/{id}/messages`. Not yet decided whether this needs
  a real fix.
- **`NullPool` needs re-evaluation** once this pool serves live HTTP
  requests under uvicorn's single persistent event loop — still flagged
  in `app/db/session.py`'s own comment, still not acted on.
- **Decimal-valued rows still serialize as JSON strings, not numbers** —
  carried over unchanged, visible in the frontend's raw `content_json`
  rendering (and will matter once the chart slice needs numeric `y`
  values from real rows).
- **`plans/logs/_auto-capture.md` remains silently uncommitted across
  every commit** (pre-existing workflow gap, by design of the capture
  hook's timing) — flagged for 10+ commits now with no fix proposed.
- `tests/test_seed_idempotency.py`'s own real Postgres deadlock (M1-era,
  unrelated code) remains uninvestigated.
- Lint/type tooling on the Python side (`ruff`, `mypy`) remains
  unaddressed, carried over from every prior slice.
- The concurrency-safety pattern (session-scoped advisory locks) is still
  scoped to exactly the two test classes it was originally applied to.
- Starlette's `TestClient` still emits the `httpx2` deprecation warning —
  harmless, not acted on.
- `Conversation`'s `user_id` FK to `users` is deliberately omitted —
  `users` doesn't exist yet (F8).

## Next slice (the brief, written NOW while context is hot)

Goal:
Render `analysis.chart_spec` as a real chart (via ECharts) beneath each
assistant message in the chat UI, when the data is chartable, using the
real `chart_spec`/`rows` data that now flows through
`/api/conversations/{id}/messages` end-to-end.

Constraints:
- New frontend dependencies, approved this session: `echarts` +
  `echarts-for-react` (PRD.md's named stack; the React wrapper avoids
  hand-rolling imperative lifecycle/resize management). No other new
  dependency without asking again.
- `chart_spec` has NO fixed schema (see HANDOFF's Open questions) — real
  observed shapes vary (`x`/`y` vs `x_field`/`y_field`; a non-chartable
  result as either `{"chart_type": "none", ...}` or a plain `{}`). The
  chart component must be defensive, not assume one exact shape: treat
  any `chart_spec` that doesn't resolve to a recognized `chart_type`
  (start with `"bar"` only, since that's the only type observed in real
  output so far) AND a resolvable x-field/y-field pair present in `rows`'
  own keys as "not chartable" and render nothing chart-related for that
  message (no error, no placeholder chart) — never guess or fabricate
  axes from a malformed spec.
- Do NOT touch `analyze_answer.py`, `prompts/analyze.md`, or
  `AnalyzeResponse` — tightening `chart_spec`'s schema is explicitly a
  separate future slice (this session's decision).
- Follow the established frontend conventions: Tailwind utility classes
  inline (no CSS modules/stylesheets), plain function components with
  inline-destructured typed props, no new state-management library.
  `web/src/api.ts`'s `ConversationMessageResult` interface (currently
  missing `analysis` entirely — stale relative to the backend) and
  `MessageDetail`'s consumers need a matching `analysis` shape added.
- New component file (e.g. `web/src/components/ChartView.tsx` or
  similar) rather than growing `App.tsx` further — first split into a
  `components/` directory, since chart rendering is a distinct concern
  from the conversation-list/compose-form code already there.
- No backend changes.

Inputs:
- `web/src/App.tsx` lines 92-103 (`ConversationDetailView`'s message
  rendering loop — the only place assistant content renders today) and
  its surrounding `stale`-flag async-guard pattern.
- `web/src/api.ts` (full file) — `MessageDetail.content_json:
  Record<string, unknown>`, `ConversationMessageResult` (needs the
  `analysis` field added), `fetchConversation()`/`postConversationMessage()`.
- `app/pipeline/analyze_answer.py`'s `AnalyzeResponse` (`chart_spec:
  dict[str, Any]`, no further validation) and `prompts/analyze.md` (no
  fixed chart_spec schema) as the ground truth for what shapes are
  actually possible, for read-only reference — not to be modified.
- Real observed `chart_spec` examples: this handoff's own Proof
  (`{"chart_type":"none","reason":...}` for a scalar result) and the
  wire-analyze-answer slice's own proof
  (`{'chart_type': 'bar', 'x': ..., 'y': ..., 'orientation': ...,
  'title': ...}` for a groupable result) — use both as real fixtures,
  not hypothetical ones.
- PRD.md's frontend stack section (names Apache ECharts) and M5's
  milestone description (chart + SQL viewer + follow-up chips) for
  scope boundaries.

Outputs:
- `web/package.json` gains `echarts` + `echarts-for-react`.
- `web/src/api.ts`: `ConversationMessageResult` (and any shared
  `Analysis`-shaped interface used by both it and message rendering)
  gains an `analysis` field matching the backend's real shape.
- New `web/src/components/ChartView.tsx` (or equivalent): given a
  message's `content_json` (or its parsed `analysis`/`rows`), renders an
  ECharts bar chart when `chart_spec`/`rows` resolve to a recognized,
  chartable shape; renders nothing otherwise.
- `web/src/App.tsx`'s message-rendering loop uses the new component
  alongside (not replacing) the existing raw JSON `<pre>` dump — the "View
  SQL"/explanation collapsed section and follow-up chips remain later
  slices' work, so the raw dump stays as the fallback view for everything
  the chart doesn't cover yet.

Done-check:
Start the dev server (`docker compose up` or `npm run dev` + the API),
ask a real chartable question (e.g. "What are the top 5 product
categories by number of orders?") through the chat UI, and screenshot
(via CDP) the message showing a real rendered bar chart beneath it — then
ask a real non-chartable scalar question (e.g. "How many orders have the
status 'delivered'?") and screenshot showing no chart renders (no error,
no empty chart box) for that message.

Out-of-scope:
- Any chart type other than bar (line/pie/table) — add when real output
  actually produces one; speculative support for unobserved shapes is
  not this slice's job.
- Tightening `chart_spec`'s schema in `prompts/analyze.md`/
  `AnalyzeResponse` — deferred, this session's explicit decision.
- The "View SQL"/explanation collapsed section and follow-up chips —
  separate M5 slices.
- Any backend change.
- Pinning charts to a dashboard (M6).
