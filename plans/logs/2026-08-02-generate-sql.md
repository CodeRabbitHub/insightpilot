# Slice log — Generate SQL from a fixed question

Date: 2026-08-02
Brief: plans/briefs/2026-08-02-generate-sql.md

## The plan you approved
For one fixed question, build the full 9-table `olist` catalog (DDL +
LLM description + columns, reusing `describe.py`'s existing fetch/format
helpers) as prompt context, call Claude once via a new versioned
`prompts/generate_sql.md`, validate the `{"sql": "..."}"` reply with a
Pydantic model requiring a single `SELECT` (one retry, matching
`describe.py`'s pattern), and return/print the raw SQL. The done-check
(`verify_generate_sql.py`) needed an alias-aware regex tokenizer (not
sqlglot, out of scope) to check referenced table/column names against a
live catalog query without false-positiving on table aliases or `AS`
output aliases — resolved at Gate 1 via a direct before/after comparison
with a concrete query shape.

## The diff you accepted
Commit `e63962a` — "Generate SQL from a fixed question: first link of
M2's text-to-SQL pipeline" (12 files changed, 1017 insertions(+)). New:
`app/pipeline/generate_sql.py`, `app/pipeline/verify_generate_sql.py`,
`prompts/generate_sql.md`, `evals/generate_sql.md`, 4 new test files. A
separate commit, `ddfc51a`, closed out the previous slice's stranded
capture/handoff artifacts first, so this diff is this slice's content
only. Full mechanics in `plans/logs/_auto-capture.md` and
`artifacts/reviews/2026-08-02-generate-sql.md`.

## The done-check output
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

## One thing you rejected or changed
Two real fixes from the Gate 2 no-slop pass:
1. `build_schema_context` had no guard for a `NULL` description — a
   not-yet-described table would have silently embedded the literal text
   "Description: None" into the LLM prompt. Changed to raise a
   `RuntimeError` naming the table instead.
2. `GenerateSqlResponse`'s validator accepted a semicolon-smuggled second
   statement (e.g. `"SELECT 1; DROP TABLE olist.orders"`) since it still
   starts with `SELECT` after stripping one trailing `;`. Changed to
   reject any remaining `;` in the stripped string.
Plus a process fix, not a code fix: the previous slice's `/capture` and
`/handoff` output (`evals/table_description.md`, its slice log, and the
`HANDOFF.md` rewrite) had never actually been committed — found sitting
in the working tree at the start of this session. Committed separately
(`ddfc51a`) rather than folded into this slice, so slice/commit boundaries
stayed honest.

## The eval
`evals/generate_sql.md` — new, this is the second LLM prompt in the
project. 1 fixed case (the brief only defines one question) against a
4-point rubric (real table/column refs, correct join, `COUNT(DISTINCT
order_id)` to avoid multi-item-order inflation, correct top-5 ordering).
Graded by running the generated SQL directly against the real DB. 1/1
pass.

## The next smallest slice
Validate the generated SQL for real: parse it with `sqlglot`, confirm
it's a single read-only `SELECT` (reject any DDL/DML/multi-statement at
the parser level, not just Pydantic's string check), and confirm every
table/column it references against the catalog the same way
`verify_generate_sql.py` does today — but as the actual pipeline gate
`generate_sql.py`'s caller will run before execution, replacing today's
lightweight regex tokenizer with a real one. Still no execution yet
(needs the read-only asyncpg pool, a separate slice after this).
