# Review gate — Generate SQL from a fixed question

Date: 2026-08-02
Brief: plans/briefs/2026-08-02-generate-sql.md
Diff reviewed: working tree vs HEAD (ddfc51a), pre-commit

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review
```
 app/pipeline/__init__.py                 |   0
 app/pipeline/generate_sql.py             | 108 ++++++++++++++++++
 app/pipeline/verify_generate_sql.py      | 125 ++++++++++++++++++++
 plans/briefs/2026-08-02-generate-sql.md  |  75 ++++++++++++
 plans/logs/_auto-capture.md              |  23 ++++
 prompts/generate_sql.md                  |  29 +++++
 tests/_generate_sql_helpers.py           |  29 +++++
 tests/test_generate_sql_cli.py           | 148 ++++++++++++++++++++++++
 tests/test_generate_sql_prompt_file.py   |  93 +++++++++++++++
 tests/test_verify_generate_sql_script.py | 190 +++++++++++++++++++++++++++++++
 10 files changed, 820 insertions(+)
```
(`plans/logs/_auto-capture.md`'s entry here is the capture_commit hook's
mechanical append of the *previous* commit, `ddfc51a` — pre-existing
plumbing, not this slice's content. `evals/generate_sql.md`, written
during this gate's Check 3, is staged separately and described there.)
Reviewable: every file was read in full during build; no file exceeds a
couple hundred lines and each has a single clear responsibility. PASS.

## 2. The stated goal matches the actual change
Brief's Goal: for one fixed, hardcoded question, generate a single SQL
`SELECT` via one Claude API call using the full `olist` catalog as
context, and print the raw SQL to stdout.

What the diff does: `app/pipeline/generate_sql.py` does exactly this —
`FIXED_QUESTION` is hardcoded, `build_schema_context` covers all 9
tables via `describe.py`'s existing `fetch_tables`/`fetch_columns`/
`format_columns_context` (reused, not duplicated), one Claude call with
one retry via `GenerateSqlResponse` (Pydantic, requires a single `SELECT`
statement), `generate_sql()` returns the string, `main()` prints it.
`app/pipeline/verify_generate_sql.py` is exactly the done-check the brief
asked for: starts-with-SELECT plus an alias-aware live-catalog reference
check, never a hardcoded table/column list. No unrequested scope — no
sqlglot, no LIMIT/timeout injection, no execution against any DB, no
retrieval, no multi-question CLI support. PASS.

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
.....................................................................................
----------------------------------------------------------------------
Ran 85 tests in 53.988s

OK
```
This is the second LLM-driven prompt in the project (`prompts/
generate_sql.md`) — per CLAUDE.md, a prompt change needs an eval.
`evals/generate_sql.md` was written during this check: a 1-case, R1-R4
rubric (real table/column refs, correct join, `COUNT(DISTINCT order_id)`
to avoid multi-item-order inflation, correct top-5 ordering), graded by
executing the generated SQL directly against the real `olist` DB
(one-off, outside the pipeline — the pipeline itself never executes
generated SQL, matching the brief's out-of-scope) and confirming a sane,
strictly-descending 5-row result. 1/1 pass. PASS.

## 4. The no-slop review found no unresolved issues
no-slop-reviewer subagent findings and resolution:
1. **Fixed** — `build_schema_context` had no guard for a `NULL`
   description, so a not-yet-described table would silently embed the
   literal string "Description: None" into the prompt instead of failing
   loudly. Now raises `RuntimeError` naming the table if any description
   is `NULL`.
2. **Fixed** — `GenerateSqlResponse`'s validator accepted a string like
   `"SELECT 1; DROP TABLE olist.orders"` since it still starts with
   `SELECT` after stripping one trailing semicolon. Now rejects any
   remaining `;` in the stripped string, so a smuggled second statement
   fails Pydantic validation.
3. **Documented, not fixed** — `check_references`'s alias detection
   doesn't recognize a bare subquery alias (`(SELECT ...) sub`, no `AS`,
   no `olist.` prefix before it) and would flag it as unknown. Out of
   proportion to fix for a "lightweight sanity check" that sqlglot
   supersedes next slice; added as an explicit limitation in the
   function's docstring.
4. **Disclosed exception, not a defect** — no test forces the
   retry-exhausted / API-down path, because forcing it would require
   mocking the Anthropic response, against this project's real-
   infrastructure-only test convention. Same accepted precedent as
   `test_describe_cli.py`'s equivalent note.
5. **Process finding, resolved separately** — the reviewer also caught
   that `evals/table_description.md`, `plans/logs/2026-08-02-llm-table-
   descriptions.md`, and a `HANDOFF.md` rewrite from the *previous* slice
   were sitting uncommitted in the working tree (never part of `a657fd6`).
   Committed separately as `ddfc51a` before this slice's diff, per user
   direction, so this gate's diff is this slice's content only.
Categories 1/3(beyond the brief-mandated `describe.py`-pattern
duplication, already an accepted exception)/4/6/7 (dead code, naming,
comments, consistency — correct reuse of `describe.py`/`sync.py` helpers)
reported clean. Everything above was fixed or explicitly documented; no
unresolved findings remain. PASS.

## 5. The shipping proof is attached
Real run against the live docker-compose Postgres and the real Anthropic
API this session (not mocked), plus a direct execution of the generated
SQL to prove it's not just syntactically valid but actually correct:
```
$ python -m app.pipeline.verify_generate_sql
Generated SQL:
SELECT p.product_category_name, COUNT(DISTINCT oi.order_id) AS num_orders FROM olist.order_items oi JOIN olist.products p ON oi.product_id = p.product_id GROUP BY p.product_category_name ORDER BY num_orders DESC LIMIT 5

verify_generate_sql: PASSED

$ python -c "... execute the generated SQL directly via app.catalog.sync.connect() ..."
('cama_mesa_banho', 9417)
('beleza_saude', 8836)
('esporte_lazer', 7720)
('informatica_acessorios', 6689)
('moveis_decoracao', 6449)
```
Five categories, strictly descending, sane counts against the real Olist
data. PASS.

## Rejected or changed
- Fixed the two real defects the no-slop-reviewer found (silent-None
  schema context, semicolon-smuggled multi-statement SQL) — see Check 4.
- Committed the previous slice's stranded capture/handoff artifacts as
  their own commit (`ddfc51a`) rather than folding them into this slice's
  commit, after asking the user which they preferred.

## Verdict
accept — all five checks green.
