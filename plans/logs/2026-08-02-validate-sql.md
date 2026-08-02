# Slice log — sqlglot SQL validator

Date: 2026-08-02
Brief: plans/briefs/2026-08-02-validate-sql.md

## The plan you approved
Add `validate_sql(sql, cur)` in a new `app/pipeline/validate_sql.py`:
parse with sqlglot's Postgres dialect, reject anything but a single
`SELECT`, check every table reference via an AST walk against
`app.catalog_tables`, and check every column reference via sqlglot's own
`optimizer.qualify` (scope-aware — handles aliases and `ORDER BY
<output_alias>` correctly, unlike the regex it replaces) against
`app.catalog_columns`. Wire `verify_generate_sql.py` to call it instead
of the old `check_references`/`fetch_valid_names`/regex constants, which
get deleted. Approach was prototyped live against sqlglot before Gate 1
to confirm the design actually worked, not just planned in the abstract.

## The diff you accepted
Commit `cf0b452` — "sqlglot SQL validator: replace the regex
reference-checker with real parsing" (7 files changed, 551 insertions(+),
190 deletions(-)). New: `app/pipeline/validate_sql.py`,
`artifacts/reviews/2026-08-02-validate-sql.md`,
`plans/briefs/2026-08-02-validate-sql.md`. Full mechanics in
`plans/logs/_auto-capture.md` and `artifacts/reviews/2026-08-02-validate-sql.md`.

## The done-check output
```
$ python -m app.pipeline.verify_generate_sql
Generated SQL:
SELECT p.product_category_name, COUNT(DISTINCT oi.order_id) AS num_orders FROM olist.order_items oi JOIN olist.products p ON oi.product_id = p.product_id GROUP BY p.product_category_name ORDER BY num_orders DESC LIMIT 5

verify_generate_sql: PASSED

$ python -m unittest discover tests
...........................................................................................
----------------------------------------------------------------------
Ran 91 tests in 55.546s

OK
```

## One thing you rejected or changed
Four successive no-slop-reviewer passes on one function
(`check_table_references`), each finding a real validation bypass the
previous fix didn't fully close:
1. Checking only `table.name` let `pg_catalog.products` (wrong schema,
   real basename) through undetected. Fixed: also check `table.db`.
2. The CTE-name exemption fired on bare basename before the schema check,
   so a CTE named e.g. `products` masked a qualified reference to
   `pg_catalog.products` elsewhere in the same query — bug 1 reopened
   through a different path. Fixed: exemption now requires no qualifier
   at all.
3. `.db` alone doesn't cover every qualifier shape sqlglot exposes; a
   `catalog..table` double-dot form left `.db` empty while `.catalog`
   carried the text, bypassing the check a third time. Fixed by
   redesigning as an allowlist — combine every qualifier field sqlglot's
   `exp.Table` exposes (`catalog`, `db` — confirmed via `arg_types` these
   are the only two) into one string that must equal exactly `"olist"`
   if present at all, instead of blocklisting known-bad values one field
   at a time.
4. Two non-bypass defects found on a fourth targeted pass: a
   table-valued function call (`generate_series(1,10)`) produced a
   nonsensical `unknown table(s) referenced: olist.` message (empty
   `.name`); and the qualifier check was case-insensitive while the
   table/CTE-name checks weren't, so a real reference like `olist.ORDERS`
   was wrongly rejected. Both fixed; regression test added for each of
   the four bugs.

**This is worth promoting**: every one of the four bugs was the same
shape — a blocklist check ("reject known-bad") missing a field or a case
the author hadn't enumerated, rather than an allowlist check ("must
exactly match the one known-good shape"). Proposing a `templates/
no-slop.md` line for security/identifier-validation logic specifically:
prefer allowlist over blocklist, and enumerate every field a value can
carry (checked via the library's own type introspection, e.g.
`arg_types`) before trusting a single-field check.

Separately, an unrelated pre-existing test
(`test_llm_description_setup.py::test_requirements_gains_no_other_new_dependencies`)
hardcoded a dependency allow-list from an earlier slice and broke when
this slice's own pre-approved `sqlglot` dependency was added — its design
(reading the live `requirements.txt` rather than a historical snapshot)
means it can never coexist with a later slice's approved dependency.
Raised to the user directly rather than silently patched; user chose to
extend the allow-list with a comment, not delete or weaken the test's
real guarantee.

## The next smallest slice
Add ARCHITECT.md's defense-in-depth layer 3 (injected `LIMIT 1000` +
`statement_timeout` 10s) and execute the now-validated SQL for real
against a new asyncpg read-only pool (`OLIST_RO_USER`, already
provisioned in M1) — completing M2's "question → SQL → validate →
execute → printed answer" with the fixed question, printing the actual
result rows. New dependency: `asyncpg`.
