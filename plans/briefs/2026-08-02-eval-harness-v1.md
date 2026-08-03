# Brief — eval harness v1

Date: 2026-08-02
Milestone: M3 Retrieval + repair + evals (eval harness with the first
accuracy number)

Goal:
`python -m evals.run` runs 5 curated real-world questions through the
real pipeline (`answer.get_answer()`) and reports a per-question
pass/fail plus an overall accuracy score.

Constraints:
Start with exactly 5 questions, per `templates/eval.md`'s "start with 5"
and PRD.md §10's eventual 30 being an M8 (not M3) target. Each question
needs a real expected-result assertion (e.g. a specific top value, a
specific count) hand-verified against the real `olist` database during
this slice — never invented or copied from an LLM's guess. Grading is
exact-match or code-assertion only, no LLM-as-judge — same bar
`evals/generate_sql.md`/`evals/table_description.md` already set. New
dependency: `PyYAML`, to parse `evals/questions.yaml` (already pulled in
transitively by `voyageai`, but every other dependency in
`requirements.txt` is pinned explicitly — confirm the exact version
pin at Gate 1). To run more than `FIXED_QUESTION`, `generate_sql()` and
`get_answer()` each gain an optional `question` parameter defaulting to
`FIXED_QUESTION` — every existing CLI entrypoint
(`python -m app.pipeline.generate_sql`, `python -m app.pipeline.answer`)
and both verify scripts must keep their exact current behavior with zero
changes on their end, proven by the full existing test suite passing
unchanged. `validate_sql.py`/`execute_sql.py` need no changes — they
already operate on a raw SQL string, not a question.

Inputs:
PRD.md §10 (eval spec: `evals/questions.yaml`, accuracy scoring, the
eventual 30-question/≥80% targets); `templates/eval.md` (case-table
shape); `evals/generate_sql.md` and `evals/table_description.md` (this
project's own eval-log precedent, including the LLM-as-judge deferral
threshold); `app/pipeline/answer.py`'s `get_answer()`;
`app/pipeline/generate_sql.py`'s `generate_sql()` and `FIXED_QUESTION`;
the real `olist` schema, for hand-verifying the 5 questions' expected
assertions.

Outputs:
- `requirements.txt` gains `PyYAML` (pinned).
- `evals/questions.yaml` — 5 curated questions, each with an expected
  assertion checkable in code (exact shape proposed at Gate 1, e.g.
  `{question: "...", expected: {top_row: ["beleza_saude", 8836]}}`).
- `evals/run.py` (+ `evals/__init__.py` if needed for `python -m
  evals.run`) — loads `questions.yaml`, calls `answer.get_answer(question)`
  per question, checks the result against its expected assertion, prints
  a per-question PASS/FAIL line and a final "N/5 correct" summary.
- `generate_sql()` and `get_answer()` gain an optional `question`
  parameter (default `FIXED_QUESTION`) threaded through
  `retrieve_relevant_tables()`/`build_schema_context()`/
  `call_llm_for_sql()` — no other behavior change.
- Tests: the parameterization doesn't change `FIXED_QUESTION`'s default
  behavior (full existing suite passes unchanged); the eval runner
  correctly reports pass/fail against a known-good and a known-bad
  fixture case.

Done-check:
`python -m evals.run` exits 0 and prints a real accuracy score (e.g.
"5/5 correct" or honestly fewer) for the 5 curated questions — paste
output. Separately, `python -m unittest discover tests` still passes in
full, proving the `question` parameter change didn't alter any existing
CLI's default behavior — paste output.

Out-of-scope:
Reaching PRD's eventual 30-question set or its ≥80% ship-gate
enforcement (M8), the one-shot repair loop, business glossary retrieval
(F5), any new CLI flag for end-user-supplied arbitrary questions in a
production surface (M4/M5), changes to `validate_sql.py`/
`execute_sql.py` internals, LLM-as-judge grading, FastAPI/frontend, CI.
