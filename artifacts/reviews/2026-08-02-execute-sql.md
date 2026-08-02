# Review gate — execute-sql

Date: 2026-08-02
Brief: plans/briefs/2026-08-02-execute-sql.md
Diff reviewed: working tree staged diff (pre-commit), 11 files, 643 insertions, 0 deletions

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review
```
app/pipeline/answer.py                      |  45 ++++++++
app/pipeline/execute_sql.py                 |  55 ++++++++++
app/pipeline/verify_answer.py               |  31 ++++++
plans/briefs/2026-08-02-execute-sql.md      |  77 ++++++++++++++
requirements.txt                            |   1 +
tests/_answer_helpers.py                    |  29 ++++++
tests/test_execute_sql_limit_cap.py         | 155 ++++++++++++++++++++++++++++
tests/test_execute_sql_ro_role.py           | 109 +++++++++++++++++++
tests/test_execute_sql_statement_timeout.py |  42 ++++++++
tests/test_llm_description_setup.py         |   5 +
tests/test_verify_answer_script.py          |  94 +++++++++++++++++
11 files changed, 643 insertions(+)
```
Three small new implementation files (~131 lines total); the rest is the
brief, tests, and a one-line requirements.txt addition plus a 5-line
extension to an existing dependency allow-list. Read line by line. PASS.

(Note: `plans/logs/_auto-capture.md` shows as separately modified in the
working tree — that's the capture_commit hook's trailing append from the
*previous* slice's commit, not part of this diff. Left unstaged; /capture
will pick it up.)

## 2. The stated goal matches the actual change
Brief's Goal: execute the validated SQL for the fixed question against a
new read-only asyncpg connection and print the real result rows,
completing M2's question → SQL → validate → execute → printed answer
chain.

What the diff does: adds `app/pipeline/execute_sql.py` (`cap_limit()` —
pure sqlglot-AST LIMIT injection/capping, and `execute_sql()` — opens one
asyncpg connection authenticated as `OLIST_RO_USER`, sets a `SET LOCAL
statement_timeout = '10s'` inside a transaction, fetches rows); adds
`app/pipeline/answer.py` (`get_answer()` chaining `generate_sql()` →
`validate_sql()` → `execute_sql()`, plus `print_answer()`); adds
`app/pipeline/verify_answer.py` (the done-check CLI, mirroring
`verify_generate_sql.py`'s PASSED/FAILED/exit-code contract); pins
`asyncpg==0.31.0` in requirements.txt (pre-approved by ARCHITECT.md's own
wording, same precedent as `sqlglot`); extends
`test_llm_description_setup.py`'s dependency allow-list accordingly.

Confirmed via `git diff` that `generate_sql.py`, `validate_sql.py`, and
`verify_generate_sql.py` are byte-identical to the prior commit — no
scope creep into upstream modules. No chart/explanation step, no repair
loop, no glossary/retrieval, no FastAPI/frontend, no CI, no persistent
connection pooling, no multi-question support — matches Out-of-scope
exactly. Goal and diff match. PASS.

## 3. The eval or test passed
Done-check, run fresh:
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
```
Same 5 rows, same strictly-descending `order_count`, `LIMIT 5` intact —
matches the prior slice's reference proof.

Full suite, run fresh:
```
$ python -m unittest discover tests
........................................................................................................
----------------------------------------------------------------------
Ran 104 tests in 79.799s

OK
```
104 = prior 91 + 13 new (6 pure `cap_limit` cases including the
non-literal-LIMIT regression added during this gate, 2 read-only-role
integration tests, 1 statement_timeout-cancellation test, 3 CLI
done-check tests, 1 requirements-allowlist assertion already counted
above). PASS.

## 4. The no-slop review found no unresolved issues
no-slop-reviewer subagent (read-only) ran against the full diff. Three
findings, all fixed before this gate:

1. **[category 5, untested edge]** `cap_limit()` assumed every existing
   `LIMIT` is a plain integer literal; a non-literal form (e.g. `LIMIT
   (SELECT ...)`) would raise an uninformative `TypeError` inside this
   defense-in-depth layer. Fixed: `cap_limit` now raises
   `SqlValidationError` naming the unsupported expression; a regression
   test (`test_a_non_literal_limit_expression_is_rejected_with_a_clear_error`)
   locks it in.
2. **[category 3, duplication]** `answer.main()` and
   `verify_answer.run()` each independently printed the SQL + rows block.
   Fixed: extracted `print_answer(sql, rows)` into `answer.py`;
   `verify_answer.py` now imports and calls it instead of keeping a second
   copy.
3. **[category 3, duplication]** `DIALECT = "postgres"` was redefined in
   `execute_sql.py` instead of importing the existing constant from
   `validate_sql.py` (which `execute_sql.py` already imports
   `parse_single_select` from). Fixed: now imports `DIALECT` from
   `validate_sql.py`.

All other categories (dead code, naming, comments, consistency, scope,
fake done, verified-not-claimed) reported clean by the reviewer, who also
independently re-ran the done-check and full suite. Re-ran both myself
after the three fixes (above) — still green. No unresolved findings
remain. PASS.

## 5. The shipping proof is attached
See Check 3's `verify_answer` output above — real rows, executed for real
through the `OLIST_RO_USER` asyncpg connection (not asserted: the
integration test suite separately proves a write attempt through the same
credentials is denied with `asyncpg.exceptions.InsufficientPrivilegeError`,
and a `pg_sleep(11)` query is cancelled by the 10s `statement_timeout`).
PASS.

## Rejected or changed
Changed three things found by the no-slop pass (not rubber-stamped):
the unhandled non-literal-LIMIT edge case, the duplicated print block
between `answer.py`/`verify_answer.py`, and the duplicated `DIALECT`
constant. All three fixed and reverified before this record was written.

## Verdict
accept — all five checks green.
