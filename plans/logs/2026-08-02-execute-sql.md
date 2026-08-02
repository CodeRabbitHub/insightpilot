# Slice log — execute-sql

Date: 2026-08-02
Brief: plans/briefs/2026-08-02-execute-sql.md

## The plan you approved
Add `app/pipeline/execute_sql.py` with a pure `cap_limit(sql, cap=1000)`
that edits the sqlglot-parsed statement's `Limit` node directly (never
string-munging) — adds a `LIMIT 1000` if none exists, tightens a looser
one, never loosens a tighter one — and an async `execute_sql(sql)` that
opens one asyncpg connection authenticated as `OLIST_RO_USER`, sets a
query-scoped `SET LOCAL statement_timeout = '10s'` inside a transaction,
executes the capped SQL, and returns rows. `app/pipeline/answer.py`
chains `generate_sql()` → `validate_sql()` → `execute_sql()`;
`app/pipeline/verify_answer.py` is the done-check CLI, mirroring
`verify_generate_sql.py`'s PASSED/FAILED/exit-code contract. New
dependency `asyncpg`, pre-approved by ARCHITECT.md's own two-pool wording
(same precedent as `sqlglot` the slice before).

## The diff you accepted
Commit `8fa281f` — "Execute validated SQL for real via a read-only
asyncpg connection" (12 files changed, 778 insertions(+)). New:
`app/pipeline/execute_sql.py`, `app/pipeline/answer.py`,
`app/pipeline/verify_answer.py`, `artifacts/reviews/2026-08-02-execute-sql.md`,
`plans/briefs/2026-08-02-execute-sql.md`, five new test files. Full
mechanics in `plans/logs/_auto-capture.md` and
`artifacts/reviews/2026-08-02-execute-sql.md`.

## The done-check output
```
$ python -m app.pipeline.verify_answer
SQL:
SELECT p.product_category_name, COUNT(DISTINCT oi.order_id) AS order_count FROM olist.order_items oi JOIN olist.products p ON oi.product_id = p.product_id GROUP BY p.product_category_name ORDER BY order_count DESC LIMIT 5

Rows:
{'product_category_name': 'cama_mesa_banho', 'order_count': 9417}
{'product_category_name': 'beleza_saude', 'order_count': 8836}
{'product_category_name': 'esporte_lazer', 'order_count': 7720}
{'product_category_name': 'informatica_acessorios', 'order_count': 6689}
{'product_category_name': 'moveis_decoracao', 'order_count': 6449}

verify_answer: PASSED

$ python -m unittest discover tests
........................................................................................................
----------------------------------------------------------------------
Ran 104 tests in 79.799s

OK
```
Same 5 rows, same strictly-descending order, `LIMIT 5` intact — matches
the prior slice's reference proof. M2 Pipeline v0 is now fully proven
end to end for the fixed question.

## One thing you rejected or changed
Three findings from the no-slop-reviewer pass, all fixed before Gate 2:
1. **Unhandled edge case** — `cap_limit()` assumed every existing `LIMIT`
   is a plain integer literal; a non-literal form (e.g. `LIMIT (SELECT
   ...)`) would have raised an uninformative `TypeError` inside this
   defense-in-depth layer instead of failing closed with a clear reason.
   Fixed: raises `SqlValidationError` naming the unsupported expression;
   locked in with a regression test.
2. **Duplication** — `answer.main()` and `verify_answer.run()` each
   independently printed the same SQL+rows block. Fixed: extracted
   `print_answer()` into `answer.py`, reused by `verify_answer.py`.
3. **Duplication** — `DIALECT = "postgres"` was redefined in
   `execute_sql.py` instead of importing the existing constant from
   `validate_sql.py` (a module it already imports `parse_single_select`
   from). Fixed: imports `DIALECT` from `validate_sql.py`.

No pattern-repeat from a previous log (the validate-sql slice's promoted
lesson was allowlist-vs-blocklist for identifier validation — a different
shape) — no new CLAUDE.md/no-slop.md promotion proposed this slice.

## The next smallest slice
M2 Pipeline v0 is complete; M3 (Retrieval + repair + evals) starts next.
Smallest cut: embed table/column descriptions into pgvector and swap
`generate_sql.py`'s `build_schema_context()` from passing the whole
catalog to top-k retrieval — the foundational piece both glossary
retrieval and the eval harness build on.
