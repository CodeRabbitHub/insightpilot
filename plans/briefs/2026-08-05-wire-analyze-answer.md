# Brief — wire analyze_answer into get_answer()

Date: 2026-08-05
Milestone: M4 API → M5 Chat UI (backend prerequisite; last wiring step
  before chart rendering, the "View SQL" explanation section, and
  follow-up chips can be built against real data)

Goal:
Wire the already-proven `analyze_answer()` into the real pipeline:
`get_answer()` calls it internally right after a successful
validate+execute, and its result flows through `app/main.py`'s response
models and message persistence so every existing endpoint's JSON response
carries real summary/explanation/chart_spec/follow_ups data.

Constraints:
- `get_answer()` (`app/pipeline/answer.py`) calls `analyze_answer(question,
  sql, rows)` itself, internally, immediately after `_answer_with_repair()`
  succeeds — not left to each of the three call sites in `app/main.py` to
  invoke separately.
- `get_answer()`'s new return shape is `(sql, rows, analysis)` — a 3-tuple,
  keeping the existing positional-unpack convention rather than switching
  to a dict/dataclass return, to minimize churn at existing call sites.
- If `analyze_answer()` raises (LLM failure after its own exhausted
  retry), that failure propagates uncaught out of `get_answer()` exactly
  like an unrepaired `validate_sql()`/`execute_sql()` failure already does
  today — no partial/degraded response, no silent fallback (CLAUDE.md's
  no-placeholder rule; the existing 502-mapping contract in `app/main.py`
  needs no new error-handling code for this).
- `AskResponse` and `ConversationMessageResult` (`app/main.py`) each gain a
  nested `analysis: AnalyzeResponse` field, reusing
  `app.pipeline.analyze_answer.AnalyzeResponse` directly — never
  hand-flatten its fields into a duplicate set, never a raw dict merge
  (templates/no-slop.md item 7). `_persist_exchange()`/
  `_persist_message_pair()` need no code change: both already call
  `jsonable_encoder(response)` on the whole response model.
- No new dependencies; no change to `analyze_answer.py`, `prompts/analyze.md`,
  or `ROW_SAMPLE_CAP` — this slice only wires the already-proven module in.
- No frontend file changes.

Inputs:
- `app/pipeline/answer.py`'s current `get_answer()` (returns `(sql,
  rows)`, chains `generate_sql()` -> `_answer_with_repair()`).
- `app/pipeline/analyze_answer.py`'s `analyze_answer(question, sql, rows)
  -> AnalyzeResponse`, proven standalone last slice.
- `app/main.py`'s `AskResponse`, `ConversationMessageResult`,
  `_persist_exchange()`, `_persist_message_pair()`, and all three
  endpoints (`/api/ask`, `/api/ask/stream`,
  `/api/conversations/{conversation_id}/messages`) that currently do
  `sql, rows = await get_answer(...)` then `AskResponse(sql=sql,
  rows=rows)`.
- `app/pipeline/verify_answer.py` (done-check convention to mirror) and
  every existing test that unpacks `get_answer()`'s return
  (`tests/test_question_parameter.py`, `tests/test_answer_repair.py`, and
  any FastAPI endpoint test asserting on `AskResponse`'s shape).
- `evals/questions.yaml` + `evals/run.py` — must still grade SQL
  correctness unchanged.

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
`.venv/Scripts/python.exe -m app.pipeline.verify_answer && .venv/Scripts/python.exe -m evals.run`
— both exit 0, pasted fresh: `verify_answer` prints `summary`/
`explanation`/`chart_spec`/`follow_ups` alongside `sql`/rows, and
`evals.run` still reports 6/6 (confirming the new mandatory
`analyze_answer()` call didn't regress SQL-correctness grading).

Out-of-scope:
- Any frontend (React/TS) change — chart rendering, the "View SQL"
  section, follow-up chips: later slice(s), once real wired data exists.
- Redesigning `chart_spec`'s schema beyond `dict[str, Any]`.
- Any change to `analyze_answer.py`'s internals, `prompts/analyze.md`, or
  `ROW_SAMPLE_CAP`.
- Any change to the SQL repair loop's own semantics
  (`repair_sql.py`/`execute_sql.py`/`validate_sql.py`/`_retry_once()`) —
  `analyze_answer()` runs only after a successful `(sql, rows)`, and never
  triggers or participates in the SQL repair loop.
- Fixing the `response.content[0].text`/`ThinkingBlock` pattern in
  `generate_sql.py`/`repair_sql.py`/`describe.py` — known, pre-existing,
  out-of-scope unless it actually breaks a run.
