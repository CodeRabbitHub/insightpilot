# Brief — repair-loop

Date: 2026-08-03
Milestone: M3 Retrieval + repair + evals (this slice closes M3 out)

Goal:
When generated SQL fails `validate_sql()` or the real DB execute in
`get_answer()`, automatically retry exactly once via a new `repair_sql()`
call (the original question + the failed SQL + the real error fed to the
LLM) before giving up.

Constraints:
- Python 3.12, existing Anthropic client + `require_env` pattern
  (ARCHITECT.md); no new provider, no new dependency.
- New `prompts/repair_sql.md`, `string.Template`-based like
  `prompts/generate_sql.md` — prompts stay versioned repo files, never
  inline strings.
- Reuse the existing `GenerateSqlResponse` Pydantic model (repair also
  produces a single `{"sql": ...}` SELECT) — no new response schema, no
  scattered `json.loads`.
- Exactly one repair attempt, max 2 attempts total end-to-end (PRD F2) —
  never a loop-until-success.
- Must not change `validate_sql.py`'s/`execute_sql.py`'s own
  validation/execution rules — this slice only wires a retry around them.
- Must not change `retrieve_relevant_tables()`/
  `retrieve_relevant_glossary_entries()`/`build_schema_context()`/
  `build_glossary_context()`/`generate_sql()`'s own generation behavior.
- Tests use real, hand-crafted-invalid SQL and real errors — no mocking,
  per this project's existing test convention (mirrors how
  `validate_sql.py`'s own tests work).
- **Gate 1 resolution:** `repair_sql(question, failed_sql, error_message)`
  lives in a new `app/pipeline/repair_sql.py` (one file per pipeline step,
  matching `generate_sql.py`/`validate_sql.py`/`execute_sql.py`), reusing
  `GenerateSqlResponse` and `DEFAULT_MODEL` imported from `generate_sql.py`.
  `app/pipeline/answer.py` gains an internal
  `async def _answer_with_repair(question, sql)` — the exact function
  `get_answer()` calls after `generate_sql()` returns: it tries
  validate+execute on `sql`, and on any exception calls `repair_sql()`
  once and retries validate+execute on the repaired SQL, letting a second
  failure propagate unmodified. This is the seam a test can call directly
  with a hand-crafted broken `sql` string to prove the repair path fires,
  with no mocking and no dependency on the LLM failing on its own.

Inputs:
- PRD.md F2 (pipeline step 4: "Validate — see F3. On failure, one
  automatic repair loop, max 2 attempts total"), F3 (validation rules),
  F9/section 9 (`repair_sql.md`: "failed SQL + DB error → corrected
  SELECT").
- `app/pipeline/generate_sql.py` — `GenerateSqlResponse`,
  `call_llm_for_sql()` pattern, `PROMPT_TEMPLATE` convention,
  `MAX_RETRIES` shape to mirror at the repair-attempt-count level.
- `app/pipeline/validate_sql.py` — `SqlValidationError`.
- `app/pipeline/execute_sql.py`.
- `app/pipeline/answer.py` — `get_answer()`, the exact orchestration point
  to modify.
- `evals/questions.yaml` + `evals/run.py` — prove no regression from the
  current 6/6.

Outputs:
- `prompts/repair_sql.md`.
- A new `repair_sql()` function (module confirmed at Gate 1).
- `get_answer()` gains one-shot repair-on-failure orchestration: on
  `SqlValidationError` from `validate_sql()` or a real exception from
  `execute_sql()`, call `repair_sql()` once with the concrete error
  message, re-validate and re-execute the repaired SQL; if that also
  fails, propagate the second failure.
- Tests:
  - A real, hand-crafted-invalid-SQL + real-error integration test
    proving `repair_sql()` alone returns a different, validation-passing
    SELECT.
  - An integration test proving `get_answer()` actually invokes the
    repair path and succeeds when the first `generate_sql()` result would
    fail (needs a concrete way to force a real first-attempt failure
    without mocking — to be settled explicitly at Gate 1).
  - `evals/run.py`'s score re-reported (still 6/6, or an honestly
    different number with an explanation).

Done-check:
All three, pasted, in one sitting: (1) the dedicated repair-path test run
standalone, demonstrating the loop fires and self-corrects on real,
deliberately invalid SQL + a real validation/DB error; (2)
`python -m evals.run` exits 0 with no regression from 6/6; (3)
`python -m unittest discover tests` passes in full (expect ~20-30 min
real runtime per CLAUDE.md — not hung).

Out-of-scope:
- Changing `generate_sql()`'s/retrieval's own generation behavior.
- Changing `validate_sql.py`'s/`execute_sql.py`'s validation/execution
  rules themselves (only wiring a retry around them).
- More than one repair attempt (no loop-until-success).
- FastAPI/frontend (M4/M5).
- CI.
- Fixing the Stop-hook/shared-DB-row concurrency hazard (still a
  separate, overdue slice of its own).
