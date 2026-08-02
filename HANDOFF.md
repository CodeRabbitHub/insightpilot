# Handoff

Date: 2026-08-02
Slice just completed: plans/briefs/2026-08-02-generate-sql.md +
  plans/logs/2026-08-02-generate-sql.md (commit e63962a)

## State of the work
- M2 Pipeline v0 now has its first link: question → SQL. No retrieval,
  no validation-by-parser, no execution yet — those are separate slices,
  per PLAN.md.
- `prompts/generate_sql.md` — new versioned prompt (`string.Template`,
  `$schema_context`/`$question` placeholders). Instructs the model to
  return exactly one `SELECT`, schema-qualified as `olist.<table>`, never
  inventing a table/column, as `{"sql": "..."}"`.
- `app/pipeline/generate_sql.py` — new package/module, CLI via
  `python -m app.pipeline.generate_sql`. `FIXED_QUESTION = "What are the
  top 5 product categories by number of orders?"`. `build_schema_context`
  covers all 9 `olist` tables (reuses `app.catalog.describe`'s
  `fetch_tables`/`fetch_columns`/`format_columns_context` rather than
  duplicating them — raises `RuntimeError` if any table's `description`
  is still `NULL`, so a partially-described catalog fails loudly instead
  of silently embedding "Description: None" into the prompt).
  `GenerateSqlResponse` (Pydantic) requires a single `SELECT` statement —
  rejects non-SELECT and rejects any remaining `;` after stripping one
  trailing semicolon, so a smuggled second statement fails validation.
  `call_llm_for_sql` retries once, wrapping the whole attempt (API call +
  JSON extraction + Pydantic validation), matching `describe.py`'s
  pattern exactly. `generate_sql()` returns the SQL string (doesn't
  print); `main()` prints it.
- `app/pipeline/verify_generate_sql.py` — the done-check. Confirms the
  SQL starts with `SELECT` and, via a hand-rolled alias-aware regex
  tokenizer (`check_references` — strips string literals, resolves table
  aliases from `FROM/JOIN olist.<table> <alias>` and output aliases from
  `AS <alias>`, then checks every remaining `olist.<table>` /
  `<alias>.<column>` / bare identifier against a live query against
  `app.catalog_tables`/`app.catalog_columns`), that every table/column it
  references is real. Explicitly not sqlglot (out of scope this slice);
  documented limitation: a bare subquery alias with no `AS` and no
  `olist.` prefix right before it would false-positive as unknown.
- `evals/generate_sql.md` — second LLM prompt in the project, needed its
  own eval per CLAUDE.md. 1 fixed case (the one hardcoded question)
  against a 4-point rubric, graded by executing the generated SQL
  directly against the real DB (a one-off manual check, not a pipeline
  capability) and confirming a correctly-ordered, sane 5-row result.
- `templates/no-slop.md` gained a new checklist line under Scope: a new/
  changed `prompts/*.md` file must have a matching `evals/*.md` case —
  this slice's Gate 2 caught that gap once (not yet a "caught twice"
  case, promoted anyway by explicit user choice).
- Separately committed (`ddfc51a`, before this slice's commit): the
  *previous* slice's `/capture`+`/handoff` output (`evals/
  table_description.md`, its slice log, the `HANDOFF.md` rewrite) had
  been produced last session but never actually committed — found
  sitting uncommitted at the start of this session and closed out on its
  own, so slice/commit boundaries stayed one-to-one.
- 85 tests pass (`python -m unittest discover tests`, via the project
  `.venv`) — 60 from prior slices + 25 new: prompt-file structural
  checks, module-constants/Pydantic-validator unit tests (no network),
  real end-to-end `generate_sql()`/CLI runs, and direct unit tests of
  `check_references` against hand-built SQL strings (valid aliased
  queries, a hallucinated table, a hallucinated column, keywords/
  aggregates, string-literal look-alikes).

## Proof
```
$ python -m app.pipeline.verify_generate_sql
Generated SQL:
SELECT p.product_category_name, COUNT(DISTINCT oi.order_id) AS num_orders FROM olist.order_items oi JOIN olist.products p ON oi.product_id = p.product_id GROUP BY p.product_category_name ORDER BY num_orders DESC LIMIT 5

verify_generate_sql: PASSED

$ python -m unittest discover tests
.....................................................................................
----------------------------------------------------------------------
Ran 85 tests in 53.988s

OK
```
Executed directly against the real DB (one-off, outside the pipeline) to
confirm the SQL is actually correct, not just syntactically valid:
```
('cama_mesa_banho', 9417)
('beleza_saude', 8836)
('esporte_lazer', 7720)
('informatica_acessorios', 6689)
('moveis_decoracao', 6449)
```

## Open questions / known issues
- Test runner: still `unittest`, still via the project `.venv`. Carried
  over: will likely move to pytest once FastAPI test deps land in M4 —
  that slice must update `.claude/hooks/stop_verify.py`'s TEST_CMD and
  CLAUDE.md together.
- Lint/type tooling (`ruff`, `mypy`) named in CLAUDE.md's Commands still
  aren't installed in the project `.venv` — carried over, not blocking
  yet.
- `verify_generate_sql.py`'s `check_references` is a hand-rolled regex
  tokenizer, not a real parser — documented gaps: doesn't verify an alias
  actually resolves to the table it was assigned to, validates bare
  column tokens against the full cross-table column set rather than
  per-table, and would false-positive on a bare subquery alias. All
  explicitly deferred to the sqlglot slice (next, below) per ARCHITECT.md's
  "defense in depth" ordering (sqlglot parse gate → catalog check →
  LIMIT/timeout injection → RO grants as last line of defense).
- `generate_sql()` has no "already done" cache like `describe.py` — every
  call is a real, billed Claude API call. Tests share one call per test
  class (`setUpClass`) to avoid re-billing per assertion; still costs
  real API calls across the eval + gate + this handoff's proof runs.

## Next slice (the brief, written NOW while context is hot)
Goal:
Add a `sqlglot`-based SQL validator — a new `validate_sql(sql, cur)`
function that enforces exactly one `SELECT` statement and confirms every
table/column it references resolves against `app.catalog_tables`/
`app.catalog_columns` — and use it to replace `verify_generate_sql.py`'s
hand-rolled regex tokenizer, closing the gap that slice explicitly
deferred. This is ARCHITECT.md's "defense in depth" layers 1+2 (sqlglot
parse gate, then catalog existence check) for the one fixed question's
generated SQL. Still no execution against any database.

Constraints:
New dependency, pre-approved by ARCHITECT.md's own wording ("Defense in
depth for generated SQL, in order: sqlglot parse gate ... → catalog
existence check") but still needs adding to `requirements.txt` and
confirming at Gate 1: `sqlglot` only, no other new dependencies. Parse
with sqlglot's Postgres dialect; reject (raise, no silent pass) if:
parsing fails outright, more than one statement is present, the
statement isn't a `SELECT`, or any table/column identifier it references
resolves to neither `app.catalog_tables.table_name` nor
`app.catalog_columns.column_name` (schema-qualified `olist.<table>` and
bare/alias-qualified columns both in scope — use sqlglot's own AST
walk/scope resolution for this, not new regex). Plain psycopg2 for the
catalog lookup (reuse `app.catalog.sync.connect`), no ORM. No LIMIT/
statement_timeout injection (ARCHITECT.md's layer 3, a later slice), no
execution, no changes to `generate_sql.py`'s prompt or LLM-calling logic
— this slice is purely the validation layer consuming `generate_sql`'s
existing output. `verify_generate_sql.py` keeps its role as the
done-check CLI but calls the new validator instead of `check_references`
(delete `check_references` and its now-redundant tests once the
replacement is proven equivalent-or-better).

Inputs:
ARCHITECT.md's defense-in-depth ordering and DB-pool-isolation decisions;
`plans/logs/2026-08-02-generate-sql.md`'s "next smallest slice" note;
`app/pipeline/generate_sql.py`'s real output for the fixed question (the
positive case); `app/pipeline/verify_generate_sql.py`'s existing
`check_references` test cases (the hallucinated-table/hallucinated-
column/keyword/alias scenarios) as the negative/edge cases the sqlglot
version must still handle correctly, now via real parsing instead of
regex; `app.catalog_tables`/`app.catalog_columns` as the live existence
source (never hardcoded).

Outputs:
- `requirements.txt` gains `sqlglot` (pinned to whatever version `pip
  install` resolves).
- A new module (exact path proposed at Gate 1, e.g.
  `app/pipeline/validate_sql.py`) exporting `validate_sql(sql, cur)` —
  raises a clear, specific exception (naming what's wrong: multi-
  statement, non-SELECT, or which identifier is unknown) on any
  violation, returns normally (no return value needed) if valid.
- `app/pipeline/verify_generate_sql.py` updated to call `validate_sql`
  instead of `check_references`; `check_references` and its dedicated
  unit tests removed once the new validator's own tests cover the same
  scenarios.
- Unit tests for `validate_sql` covering: the real fixed-question SQL
  (passes), a multi-statement string, a non-SELECT statement, a
  hallucinated table name, and a hallucinated column name (all four
  rejected, each with a message naming what's wrong).

Done-check:
`python -m app.pipeline.verify_generate_sql` still exits 0 for the fixed
question (now backed by real sqlglot validation, not regex) — paste its
output. Separately, a test run demonstrates `validate_sql` rejects each
of the four deliberately-invalid SQL strings above, each raising with a
message identifying the specific problem.

Out-of-scope:
LIMIT/statement_timeout injection, executing the generated SQL against
any database (the read-only asyncpg pool doesn't exist yet), the
business glossary (F5/M3), retrieval/pgvector (M3), the `analyze.md`
chart/explanation step, the repair loop, FastAPI, frontend, CI, changing
`generate_sql.py`'s prompt or LLM-calling behavior, arbitrary/multi-
question CLI support.
