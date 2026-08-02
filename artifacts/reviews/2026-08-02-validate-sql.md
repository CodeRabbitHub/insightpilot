# Review gate — sqlglot SQL validator

Date: 2026-08-02
Brief: plans/briefs/2026-08-02-validate-sql.md
Diff reviewed: working tree vs HEAD (32065a6), pre-commit

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review
```
 app/pipeline/validate_sql.py (new)       | 108 +++++
 app/pipeline/verify_generate_sql.py      |  95 +--------
 plans/briefs/2026-08-02-validate-sql.md  |  78 +++++ (new)
 requirements.txt                         |   1 +
 tests/test_llm_description_setup.py      |   5 +
 tests/test_verify_generate_sql_script.py | 328 +++++++++++++++++++++----------
```
(`plans/logs/_auto-capture.md`'s pending 26-line change predates this
session — the previous slice's capture_commit hook append that was never
folded into a commit — not this slice's content; left untouched here.)
Reviewable: every file read in full during build; `validate_sql.py` is
one new, single-responsibility module at 108 lines. PASS.

## 2. The stated goal matches the actual change
Brief's Goal: add `validate_sql(sql, cur)` — sqlglot-based, enforces
exactly one `SELECT`, confirms every table/column resolves against the
live catalog — and use it in `verify_generate_sql.py` in place of the
regex tokenizer (`check_references`).

What the diff does: exactly this. `check_table_references` walks
`exp.Table` nodes; `check_column_references` delegates to
`sqlglot.optimizer.qualify.qualify(..., validate_qualify_columns=True)`
for real scope-aware column resolution (handles aliases, per-table
ambiguity, and `ORDER BY <output_alias>` correctly — strictly better than
the regex version on this point). `check_references`/`fetch_valid_names`/
`SQL_STOPWORDS` and the regex constants are fully deleted.
`verify_generate_sql.py` shrank from 125 lines to 34. No unrequested
scope — no LIMIT/timeout injection, no execution, no changes to
`generate_sql.py`'s prompt/LLM logic. PASS.

## 3. The eval or test passed
Done-check run fresh, immediately before writing this record:
```
$ python -m app.pipeline.verify_generate_sql
Generated SQL:
SELECT p.product_category_name, COUNT(DISTINCT oi.order_id) AS num_orders FROM olist.order_items oi JOIN olist.products p ON oi.product_id = p.product_id GROUP BY p.product_category_name ORDER BY num_orders DESC LIMIT 5

verify_generate_sql: PASSED
```
```
$ python -m unittest discover tests
...........................................................................................
----------------------------------------------------------------------
Ran 91 tests in 55.546s

OK
```
No prompt file changed this slice, so no new eval case is required per
CLAUDE.md. PASS.

## 4. The no-slop review found no unresolved issues
Four no-slop-reviewer passes ran on this slice — an unusually deep loop,
because each pass on `check_table_references` found one more real gap in
the same "is this identifier actually `olist.<table>`?" logic, each
fixed and re-verified before the next pass:

1. **Fixed** — checking only `table.name` let a cross-schema reference
   (`pg_catalog.products`) bypass detection when the basename matched a
   real olist table. Added a `table.db` (schema) check.
2. **Fixed** — the CTE-name exemption fired on bare basename before the
   schema check ran, so a CTE named e.g. `products` masked a
   schema-qualified reference to the same name elsewhere in the query,
   reopening bug 1's hole. Restricted the exemption to truly unqualified
   references (`not qualifier and name in cte_names`).
3. **Fixed** — `.db` alone doesn't cover every qualifier shape sqlglot
   exposes; a `catalog..table` double-dot form left `.db` empty while
   `.catalog` carried the qualifying text, bypassing the check again.
   Redesigned as an allowlist: combine `table.catalog` + `table.db` into
   one qualifier string that must equal exactly `"olist"` if present at
   all, rather than blocklisting known-bad values field by field.
   Confirmed via `exp.Table.arg_types` that `db`/`catalog` are the only
   two naming-qualifier fields sqlglot's Table node exposes, so this
   closes the class rather than one more instance of it.
4. **Fixed** — two non-bypass defects (both fail closed, not security
   holes): (a) a table-valued function call in `FROM` (e.g.
   `generate_series(1,10)`) parses as `exp.Table` with an empty `.name`,
   producing a nonsensical `unknown table(s) referenced: olist.` message;
   now falls back to the node's own rendered SQL when `.name` is empty.
   (b) the qualifier check was case-insensitive but the table-name/CTE-name
   checks were not, so a real, valid reference like `olist.ORDERS` (Postgres
   folds unquoted identifiers to lowercase) was wrongly rejected as
   unknown; both comparisons now normalize case consistently.

A regression test was added for each of the six fixes (bugs 1–4 above,
plus the original CTE-exclusion and cross-schema cases from the first
pass) in `tests/test_verify_generate_sql_script.py`'s `ValidateSqlTests`.
A separate, unrelated finding — a stale test in
`test_llm_description_setup.py` hardcoding a dependency allow-list from
an earlier slice, which broke when `sqlglot` (this slice's own
pre-approved dependency) was added — was raised to the user directly
(not silently patched, per CLAUDE.md's "never weaken a test without
flagging it" rule); user chose to extend the allow-list with a comment
explaining why, keeping the test's real guarantee (no *other* untracked
dependency) intact.

A fourth, narrowly-scoped pass explicitly tried to find a fifth bug in
the same function and could not (multiple simultaneous bad references,
alias/name collisions, empty-vs-None table names, CTE/real-table name
sharing, and nested table-valued-function arguments were all stress-tested
live and handled correctly). No unresolved findings remain. PASS.

## 5. The shipping proof is attached
Real run against the live docker-compose Postgres and the real Anthropic
API this session (not mocked) — see Check 3's output above; same command,
re-run immediately before this record was written. PASS.

## Rejected or changed
- Fixed all four defects above (three validation bypasses of increasing
  subtlety in the same function, one message-quality/false-positive pair
  found on the fourth pass) — see Check 4.
- Extended `test_llm_description_setup.py`'s dependency allow-list to
  include `sqlglot`, per explicit user decision (asked directly rather
  than assumed), rather than silently editing or deleting the stale test.

## Verdict
accept — all five checks green.
