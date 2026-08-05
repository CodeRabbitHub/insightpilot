# Handoff

Date: 2026-08-05
Slice just completed: plans/briefs/2026-08-05-analyze-answer.md
  + plans/logs/2026-08-05-analyze-answer.md
  (commits 027a7cf, 5d0f5f6)

## State of the work
- **The text-to-SQL pipeline's last unbuilt link now exists and is proven
  standalone.** `app/pipeline/analyze_answer.py`'s `analyze_answer(question,
  sql, rows)` makes one Claude call (new `prompts/analyze.md`, a
  `string.Template` with 5 placeholders) and returns a Pydantic-validated
  `AnalyzeResponse` (`summary: str`, `explanation: str`, `chart_spec:
  dict[str, Any]`, `follow_ups: list[str]`) — same one-Claude-call /
  `extract_json_object` / one-retry / no-placeholder-fallback shape as
  `generate_sql.py`'s `call_llm_for_sql()`. Result rows are capped to
  `ROW_SAMPLE_CAP = 20` (`build_prompt()`) before being serialized into the
  prompt, verified structurally (not just behaviorally) by
  `BuildPromptRowCappingTests`.
- **Deliberately NOT wired into `get_answer()`, `app/main.py`, message
  persistence, or the frontend yet** — proven alone via
  `app/pipeline/verify_analyze_answer.py`, matching how `generate_sql.py`
  itself was originally built and proven standalone before later slices
  wired it into the full pipeline. Wiring it in is this handoff's next
  brief, below.
- **Gate 2 caught and fixed four real gaps before accept**, two by the
  no-slop pass and two others independently:
  - `prompts/analyze.md` shipped with no matching `evals/*.md` case (the
    brief's Out-of-scope note only justified skipping the automated
    `evals/questions.yaml` harness, not the manual-eval-doc precedent
    `evals/repair_sql.md` set for exactly this situation). Fixed: added
    `evals/analyze_answer.md`, two real cases — the fixed-question grouped
    result, and a real single-scalar result ("How many orders have the
    status 'delivered'?") specifically chosen to prove `chart_spec` isn't
    fabricated when nothing is meaningfully chartable (it came back a
    genuine `{}`).
  - The row-cap Constraint was only tested behaviorally (a 200-row input
    doesn't crash) — a regression removing the cap entirely would still
    pass. Fixed: added `BuildPromptRowCappingTests`, asserting the prompt's
    embedded JSON sample is exactly `rows[:ROW_SAMPLE_CAP]`.
  - `verify_analyze_answer.py` had no `try/except` matching
    `verify_answer.py`'s PASSED/FAILED convention. Fixed: added, catching
    `(SqlValidationError, RuntimeError)`.
  - **The full test suite itself (not the no-slop pass) caught a real
    bug**: `call_llm_for_analysis()` read `response.content[0].text`,
    assuming the first content block is always text — Claude returned a
    `ThinkingBlock` first for a real call (no `.text` attribute), so both
    retry attempts failed identically. Fixed with a new
    `_extract_response_text()` helper (scans for the first `type ==
    "text"` block). **This exact fragile pattern still exists, unfixed, in
    `generate_sql.py`, `repair_sql.py`, and `describe.py`** — left alone as
    pre-existing and out of scope for this slice; if it breaks a real run
    in any of those three, promote a shared `extract_response_text()`
    helper into `describe.py` (next to `extract_json_object`) instead of
    patching each site separately.
- Full gate record (all five checks green, verdict accept, includes the
  caught-and-fixed regressions above):
  artifacts/reviews/2026-08-05-analyze-answer.md.
- Full suite, run fresh, solo/foreground (to avoid racing the automatic
  Stop hook's own concurrent run, per the repair-loop slice's documented
  lesson): 304/304 passing.

## Proof
```
$ .venv/Scripts/python.exe -m app.pipeline.verify_analyze_answer
Summary:
The top 5 product categories by number of orders are cama_mesa_banho (9,417), beleza_saude (8,836), esporte_lazer (7,720), informatica_acessorios (6,689), and moveis_decoracao (6,449).

Explanation:
The query joined order_items to products on product_id, grouped by product_category_name, and counted distinct order_ids per category, then sorted descending and limited to 5 rows. The sample contains all 5 returned rows, showing cama_mesa_banho (bed/bath/table items) as the leading category, followed by health & beauty, sports & leisure, computer accessories, and furniture/decor, indicating these are the most frequently ordered product types on the platform.

Chart spec:
{'chart_type': 'bar', 'x_field': 'product_category_name', 'y_field': 'order_count', 'orientation': 'vertical', 'title': 'Top 5 Product Categories by Number of Orders', 'sort': 'descending'}

Follow-ups:
['What are the bottom 5 product categories by number of orders?', 'How do these top categories compare in total revenue rather than order count?', 'What is the average order value for each of these top 5 categories?', 'How have orders in these top categories trended over time?', 'Which sellers dominate sales in the top category, cama_mesa_banho?']

verify_analyze_answer: PASSED
```
Full suite:
```
$ .venv/Scripts/python.exe -m unittest discover tests
Ran 304 tests in 666.073s
OK
```

## Open questions / known issues
- **`get_answer()`'s LLM-call cost roughly doubles once `analyze_answer()`
  is wired in** (next brief, below) — every question already makes 2
  Voyage embeds + 1-2 Anthropic calls (generate_sql, optional repair); it
  will gain one more real Anthropic call unconditionally. Worth watching
  in `evals.run`'s wall-clock time, same shape as the glossary-retrieval
  slice's already-accepted "doubled Voyage call" cost.
- **A `response.content[0].text` / `ThinkingBlock` bug pattern, first
  occurrence** — see above. Only fixed in `analyze_answer.py` this slice;
  `generate_sql.py`, `repair_sql.py`, `describe.py` still carry the same
  fragile assumption. Not yet promoted to `templates/no-slop.md` (single
  occurrence so far, per the project's own "caught twice" ratchet rule) —
  promote a shared helper if it recurs.
- **M5 (Chat UI) backend prerequisite is now fully built but still
  unwired**: chart rendering (ECharts), the collapsed "View SQL"
  explanation section, and follow-up chips all remain unbuilt in the
  frontend, and all three are blocked on the next brief below (wiring
  `analyze_answer()` into `get_answer()`) — none of them can be built
  against real data until that's done.
- **A render-gate/loading-flag pattern to watch** (carried over,
  unrecurred): a `useEffect` re-trigger flipping a `loading` flag that a
  render gate treats as "nothing to show yet" can unmount an
  already-populated view — first (and so far only) occurrence was the
  message-composing slice's caught-and-fixed regression. Not yet promoted;
  worth naming explicitly if any future slice adds a background refresh
  to an already-rendered, `loading`-gated view.
- **The project's own `.venv` (Python 3.11.15) must be used explicitly**
  for `uvicorn`/backend commands — a bare `python`/`uvicorn` on PATH has
  resolved to an unrelated environment in a past session.
- **No frontend test runner exists** — live browser verification (via
  CDP, since chromium-cli/Playwright are unavailable here) stands in for
  it at Gate 2, for frontend-touching slices only.
- **API base URL is a hardcoded `http://localhost:8000` constant** in
  `web/src/api.ts` — open design debt, revisit only if a later slice needs
  configurable environments.
- **What happens to an already-computed answer when its persistence write
  fails**: unchanged, still a plain 500 for `/api/ask`, a silently
  truncated SSE stream for `/api/ask/stream` and
  `/api/conversations/{id}/messages`. Not yet decided whether this needs a
  real fix.
- **`NullPool` needs re-evaluation** once this pool serves live HTTP
  requests under uvicorn's single persistent event loop — still flagged in
  `app/db/session.py`'s own comment, still not acted on.
- **Real installed Python is 3.11.15** (`.venv`), not the 3.12
  ARCHITECT.md names — carried over, not investigated or acted on.
- **Decimal-valued rows still serialize as JSON strings, not numbers** —
  carried over unchanged, visible in the frontend's raw `content_json`
  rendering.
- **`plans/logs/_auto-capture.md` remains silently uncommitted across
  every commit** (pre-existing workflow gap, by design of the capture
  hook's timing — see this session's own gate record for the mechanics) —
  flagged for 10+ commits now with no fix proposed.
- `tests/test_seed_idempotency.py`'s own real Postgres deadlock (M1-era,
  unrelated code) remains uninvestigated.
- The doubled-Voyage-call-per-question design cost
  (`app/pipeline/generate_sql.py`) remains unoptimized — accepted,
  documented in code.
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
Wire the already-proven `analyze_answer()` into the real pipeline: extend
`get_answer()` to also produce the analysis (calling `analyze_answer()`
itself, internally, right after a successful validate+execute), and
thread that `AnalyzeResponse` through `app/main.py`'s `AskResponse`/
`ConversationMessageResult` models and message persistence — so the app
DB and every existing endpoint's JSON response carry real
summary/explanation/chart_spec/follow_ups data, with the frontend still
untouched.

Constraints:
- `get_answer()` calls `analyze_answer(question, sql, rows)` itself,
  internally, immediately after `_answer_with_repair()` succeeds — not
  left to each of the three call sites in `app/main.py` to invoke
  separately. This keeps `get_answer()` as "the one complete pipeline
  chain" (matching the shape `_answer_with_repair()`/`repair_sql()`
  already established) and requires only one call-site change per
  consumer (unpacking a wider return), not three separate new
  `analyze_answer()` invocations.
- `get_answer()`'s new return shape is `(sql, rows, analysis)` where
  `analysis` is the real `AnalyzeResponse` instance — a 3-tuple, keeping
  the existing positional-unpack convention (`sql, rows = await
  get_answer(...)`) rather than switching to a dict/dataclass return, to
  minimize churn at existing call sites.
- If `analyze_answer()` raises (LLM failure after its own exhausted
  retry), that failure propagates uncaught out of `get_answer()` exactly
  like an unrepaired `validate_sql()`/`execute_sql()` failure already
  does today — no partial/degraded response, no silent fallback. This
  matches CLAUDE.md's "no placeholder" standing rule and the existing
  502-mapping contract in `app/main.py`'s three endpoints (no endpoint
  code needs new error-handling logic for this specifically).
- `AskResponse` and `ConversationMessageResult` (`app/main.py`) each gain a
  nested `analysis: AnalyzeResponse` field (reusing the real
  `app.pipeline.analyze_answer.AnalyzeResponse` model directly, per
  `templates/no-slop.md` item 7 — never hand-flatten its fields into a
  duplicate set, never a raw dict merge). `_persist_exchange()`/
  `_persist_message_pair()` need no code change: both already call
  `jsonable_encoder(response)` on the whole response model, so the new
  field persists automatically once the model gains it.
- No new dependencies; no change to `analyze_answer.py`, `prompts/analyze.md`,
  or `ROW_SAMPLE_CAP` — this slice only wires the already-proven module in,
  it doesn't change its behavior.
- No frontend file changes — chart rendering, the "View SQL" section, and
  follow-up chips are all later slices' work, once real data exists to
  render.

Inputs:
- `app/pipeline/answer.py`'s current `get_answer()` (returns `(sql,
  rows)`, chains `generate_sql()` -> `_answer_with_repair()`) and
  `_retry_once()`/`_answer_with_repair()`'s existing shape, to extend
  rather than restructure.
- `app/pipeline/analyze_answer.py`'s `analyze_answer(question, sql, rows)
  -> AnalyzeResponse`, proven standalone this slice.
- `app/main.py`'s `AskResponse`, `ConversationMessageResult`,
  `_persist_exchange()`, `_persist_message_pair()`, and all three
  endpoints (`/api/ask`, `/api/ask/stream`,
  `/api/conversations/{conversation_id}/messages`) that currently do
  `sql, rows = await get_answer(...)` then `AskResponse(sql=sql,
  rows=rows)`.
- `app/pipeline/verify_answer.py` / `print_answer()` (done-check
  convention to mirror) and every existing test that unpacks
  `get_answer()`'s return (`tests/test_question_parameter.py`,
  `tests/test_answer_repair.py`, and any FastAPI endpoint test asserting
  on `AskResponse`'s shape) — these need updating to the new 3-tuple/
  nested-`analysis` shape, not left broken.
- `evals/questions.yaml` + `evals/run.py` — must still grade SQL
  correctness unchanged; re-run fresh to confirm no regression, since this
  is a pipeline-behavior change per CLAUDE.md's eval standing rule.

Outputs:
- `app/pipeline/answer.py`: `get_answer()` returns `(sql, rows, analysis)`;
  `print_answer()` (and `verify_answer.py`) updated to also print the
  analysis fields.
- `app/main.py`: `AskResponse`/`ConversationMessageResult` gain `analysis:
  AnalyzeResponse`; all three endpoints updated to unpack and forward the
  3-tuple; persistence unchanged (auto-covers the new field via
  `jsonable_encoder`).
- Every existing test/eval touching `get_answer()`'s return shape or
  `AskResponse`'s fields updated to match, still green.

Done-check:
`.venv/Scripts/python.exe -m app.pipeline.verify_answer` exits 0 with
printed output including `summary`/`explanation`/`chart_spec`/
`follow_ups` alongside `sql`/rows, pasted fresh, AND a fresh
`.venv/Scripts/python.exe -m evals.run` still reports 6/6 (confirming the
new mandatory `analyze_answer()` call didn't regress SQL-correctness
grading).

Out-of-scope:
- Any frontend (React/TS) change — chart rendering, the "View SQL"
  section, follow-up chips: later slice(s), once real wired data exists.
- Redesigning `chart_spec`'s schema beyond `dict[str, Any]` — unchanged
  from the prior slice's Constraint.
- Any change to `analyze_answer.py`'s internals, `prompts/analyze.md`, or
  `ROW_SAMPLE_CAP` — this slice only wires the already-proven module in.
- Any change to the SQL repair loop's own semantics
  (`repair_sql.py`/`execute_sql.py`/`validate_sql.py`/`_retry_once()`) —
  `analyze_answer()` runs only after a successful `(sql, rows)`, and never
  triggers or participates in the SQL repair loop itself.
- Fixing the `response.content[0].text`/`ThinkingBlock` pattern in
  `generate_sql.py`/`repair_sql.py`/`describe.py` — flagged above as a
  known, pre-existing, out-of-scope issue; not this slice's job unless it
  actually breaks a run.
