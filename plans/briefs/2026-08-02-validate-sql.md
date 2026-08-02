# Brief — sqlglot SQL validator

Date: 2026-08-02
Milestone: M2 Pipeline v0 in the CLI (question → SQL → validate → execute
→ printed answer — this slice covers only "validate", layers 1+2 of
ARCHITECT.md's defense-in-depth ordering)

Goal:
Add `validate_sql(sql, cur)` — a sqlglot-based validator that enforces
exactly one `SELECT` statement and confirms every table/column it
references resolves against `app.catalog_tables`/`app.catalog_columns` —
and use it in `verify_generate_sql.py` in place of the hand-rolled regex
tokenizer (`check_references`), closing the gap that slice explicitly
deferred.

Constraints:
One new dependency, pre-approved by ARCHITECT.md's own wording ("Defense
in depth for generated SQL, in order: sqlglot parse gate ... → catalog
existence check") — `sqlglot` only, pinned in `requirements.txt` to
whatever version `pip install` resolves, confirmed at Gate 1. Parse with
sqlglot's Postgres dialect. Raise (never silently pass) if: parsing fails
outright, more than one statement is present, the statement isn't a
`SELECT`, or any table/column identifier resolves to neither
`app.catalog_tables.table_name` nor `app.catalog_columns.column_name`
(schema-qualified `olist.<table>` and bare/alias-qualified columns both
in scope) — use sqlglot's own AST walk/scope resolution for this, not new
regex. Plain psycopg2 for the catalog lookup, reusing
`app.catalog.sync.connect` — no ORM. No LIMIT/statement_timeout injection
(ARCHITECT.md's layer 3, a later slice), no execution, no changes to
`generate_sql.py`'s prompt or LLM-calling logic — this slice is purely
the validation layer consuming `generate_sql`'s existing output.
`verify_generate_sql.py` keeps its role as the done-check CLI but calls
the new validator instead of `check_references`; delete
`check_references` and its now-redundant tests once the replacement is
proven equivalent-or-better on the same scenarios.

Inputs:
ARCHITECT.md's defense-in-depth ordering and DB-pool-isolation decisions;
`plans/logs/2026-08-02-generate-sql.md`'s "next smallest slice" note;
`app/pipeline/generate_sql.py`'s real output for the fixed question (the
positive case); `app/pipeline/verify_generate_sql.py`'s existing
`check_references` test cases (hallucinated-table, hallucinated-column,
keyword, alias scenarios) as the negative/edge cases the sqlglot version
must still handle, now via real parsing instead of regex;
`app.catalog_tables`/`app.catalog_columns` as the live existence source
(never hardcoded).

Outputs:
- `requirements.txt` gains `sqlglot` (pinned).
- A new module (exact path proposed at Gate 1, e.g.
  `app/pipeline/validate_sql.py`) exporting `validate_sql(sql, cur)` —
  raises a clear, specific exception naming what's wrong (multi-
  statement, non-SELECT, or which identifier is unknown) on any
  violation, returns normally if valid.
- `app/pipeline/verify_generate_sql.py` updated to call `validate_sql`
  instead of `check_references`; `check_references` and its dedicated
  unit tests removed once the new validator's own tests cover the same
  scenarios.
- Unit tests for `validate_sql` covering: the real fixed-question SQL
  (passes), a multi-statement string, a non-SELECT statement, a
  hallucinated table name, and a hallucinated column name (all four
  rejected, each with a message naming what's wrong).

Done-check:
`python -m app.pipeline.verify_generate_sql && python -m unittest discover tests`
— the first exits 0 for the fixed question, now backed by real sqlglot
validation instead of regex; the second shows all tests passing,
including new `validate_sql` unit tests that reject each of the four
deliberately-invalid SQL strings above, each raising with a message
identifying the specific problem. Paste both outputs.

Out-of-scope:
LIMIT/statement_timeout injection, executing the generated SQL against
any database (the read-only asyncpg pool doesn't exist yet), the
business glossary (F5/M3), retrieval/pgvector (M3), the `analyze.md`
chart/explanation step, the repair loop, FastAPI, frontend, CI, changing
`generate_sql.py`'s prompt or LLM-calling behavior, arbitrary/multi-
question CLI support.
