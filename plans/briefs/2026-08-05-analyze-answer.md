# Brief — analyze_answer pipeline step

Date: 2026-08-05
Milestone: M5 Chat UI (backend prerequisite — PRD.md F2 step 6 / §9 item 4,
  the last unbuilt piece of the text-to-SQL pipeline; unblocks chart
  rendering, the "View SQL" explanation section, and follow-up chips in a
  later M5 slice)

Goal:
Add `analyze_answer(question, sql, rows)`, a new pipeline step that makes
one Claude call with the question, the executed SQL, and a capped sample
of its result rows, and returns a Pydantic-validated `{summary,
explanation, chart_spec, follow_ups}` object.

Constraints:
- No new dependencies (CLAUDE.md; ARCHITECT.md's excluded-dependencies
  list is binding) — reuse the exact `anthropic`/`pydantic` call pattern
  `app/pipeline/generate_sql.py`'s `call_llm_for_sql()` /
  `GenerateSqlResponse` already establish: one Claude call, JSON parsed
  via `app/catalog/describe.py`'s `extract_json_object`, Pydantic
  validation with exactly one retry (`MAX_RETRIES = 1`), raising loudly —
  no placeholder fallback — if both attempts fail.
- New prompt file `prompts/analyze.md`, `string.Template`-based like
  `generate_sql.md`/`repair_sql.md` — prompts stay versioned repo files,
  never inline strings (ARCHITECT.md).
- The result rows fed into the prompt must be capped to a small sample —
  do not serialize the full up-to-1000-row result into the prompt. Exact
  cap size (candidate: 20 rows) to be finalized at Gate 1 (plan step),
  informed by PRD F1's existing 50-row display cap as a reasonable
  ceiling, not a target.
- `chart_spec` is validated only as a present JSON object
  (`dict[str, Any]`) this slice — its concrete chart-type/axis-mapping
  schema is deliberately deferred to whichever future slice actually
  renders it (ECharts); designing that schema now, with no consumer,
  would be speculative.
- `follow_ups` validated as a non-empty list of strings (PRD F1: "3-5
  suggested follow-up questions").
- Exact module path: `app/pipeline/analyze_answer.py`, matching
  `generate_sql.py`/`validate_sql.py`/`execute_sql.py`/`repair_sql.py`'s
  one-file-per-pipeline-step convention.
- Must NOT change `get_answer()`, `app/main.py`, message persistence, or
  any frontend file this slice — wiring is explicitly a later slice's job,
  so this one stays reviewable and its own contract is provable in
  isolation, matching how `generate_sql.py` was originally built and
  proven alone before later slices wired it into the full pipeline.
- All LLM JSON output goes through the Pydantic model with one retry, per
  CLAUDE.md's standing rule — no scattered `json.loads`.

Inputs:
- PRD.md F2 step 6 ("Analyze & respond — second LLM call with the result
  sample: writes the summary, explanation, chart spec ... and follow-up
  suggestions") and §9 item 4 (`analyze.md`: "question + SQL + result
  sample → JSON: {summary, explanation, chart_spec, follow_ups[]}",
  Pydantic-validated with one retry).
- `app/pipeline/generate_sql.py` (`call_llm_for_sql`, `GenerateSqlResponse`,
  `PROMPT_TEMPLATE`/`PROMPT_FILE`/`DEFAULT_MODEL`/`MAX_RETRIES` convention)
  and `app/catalog/describe.py` (`extract_json_object`) as the patterns to
  mirror exactly.
- `app/pipeline/answer.py`'s `get_answer()` return shape (`sql, rows`) —
  the exact input shape `analyze_answer()` must accept, so a later slice
  can wire `analyze_answer(question, sql, rows)` in directly.
- `app/pipeline/verify_generate_sql.py` / `verify_answer.py` as the
  done-check script convention to mirror (print result, PASSED/FAILED,
  `sys.exit`).

Outputs:
- `prompts/analyze.md`.
- `AnalyzeResponse` Pydantic model: `summary: str`, `explanation: str`,
  `chart_spec: dict[str, Any]`, `follow_ups: list[str]`.
- `app/pipeline/analyze_answer.py`: `analyze_answer(question, sql, rows) ->
  AnalyzeResponse`.
- `app/pipeline/verify_analyze_answer.py`: the done-check script — calls
  the real `get_answer()` for `FIXED_QUESTION` to get a real `(sql, rows)`
  pair (not hand-faked input), passes it to `analyze_answer()`, and
  asserts the result satisfies `AnalyzeResponse` with non-empty
  `summary`/`explanation`/`follow_ups` and a `chart_spec` dict.

Done-check:
`.venv/Scripts/python.exe -m app.pipeline.verify_analyze_answer` exits 0,
pasted fresh (per HANDOFF.md: the project's own `.venv` must be invoked
explicitly — a bare `python`/`uvicorn` on PATH resolved to an unrelated
environment last session).

Out-of-scope:
- Wiring `analyze_answer()` into `get_answer()`, `app/main.py`'s response
  models, message persistence, or any frontend rendering (charts,
  follow-up chips, the "View SQL" explanation section) — later slice(s),
  once this step's own contract is proven in isolation.
- Designing `chart_spec`'s concrete schema beyond "a JSON object" —
  deferred to the slice that actually renders it.
- Any change to `evals/questions.yaml`/`evals/run.py` — they test
  `get_answer()`'s SQL-correctness only, and `analyze_answer()` isn't
  wired into that call path yet, so there is nothing for this slice to
  regress or meaningfully extend there.
- `explain_sql.md` (PRD §9 item 5) — a separate prompt/step, not this one.
