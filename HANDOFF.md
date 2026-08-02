# Handoff

Date: 2026-08-02
Slice just completed: plans/briefs/2026-08-02-validate-sql.md +
  plans/logs/2026-08-02-validate-sql.md (commit cf0b452)

## State of the work
- M2 Pipeline v0 now has its second link fully proven: question → SQL →
  **validate** (real sqlglot parsing, not regex). Still no execution.
- `app/pipeline/validate_sql.py` — new module exporting `validate_sql(sql,
  cur)`. Parses with sqlglot's Postgres dialect (`parse_single_select`):
  rejects a parse failure, more than one statement (after filtering the
  `None` artifact from a trailing semicolon), or anything that isn't an
  `exp.Select`. `check_table_references` walks every `exp.Table` node and
  requires its combined qualifier (`table.catalog` + `table.db` — the
  only two naming-qualifier fields `exp.Table` exposes, confirmed via
  `arg_types`) to equal exactly `"olist"` if present at all, and the
  basename to be a real table in `app.catalog_tables` (case-insensitive,
  CTE names exempted only when truly unqualified). `check_column_references`
  delegates to `sqlglot.optimizer.qualify.qualify(...,
  validate_qualify_columns=True)` for real scope-aware column resolution
  (correctly handles per-table ambiguity and `ORDER BY <output_alias>`,
  which the old regex tokenizer couldn't). `fetch_catalog_schema(cur)`
  builds `{table_name: {column_name: data_type}}` live from
  `app.catalog_tables`/`app.catalog_columns` — never hardcoded.
- `app/pipeline/verify_generate_sql.py` — now calls `validate_sql(sql,
  cur)` instead of the deleted `check_references`/`fetch_valid_names`/
  `SQL_STOPWORDS`/regex constants; shrank from 125 to 34 lines. Same
  PASSED/FAILED/exit-code contract as before.
- `requirements.txt` gained `sqlglot==30.14.0` (ARCHITECT.md's own
  defense-in-depth wording pre-approved it).
- Four successive no-slop-reviewer passes on `check_table_references`
  each found one more real validation bypass before the design converged
  on an allowlist (qualifier must equal exactly `"olist"`, combining every
  qualifier field the library exposes) rather than a blocklist (reject
  specific known-bad values): a bare cross-schema reference
  (`pg_catalog.products`), a CTE name masking a qualified reference to
  itself, a `catalog..table` double-dot form that bypassed a `.db`-only
  check, and (non-bypass, fail-closed) a table-valued-function call
  producing an uninformative message plus a case-folding mismatch
  wrongly rejecting valid uppercase references. Every fix has its own
  regression test in `ValidateSqlTests`. Full history in the gate record.
- `templates/no-slop.md` gained a new line under Untested edges: for
  identifier/security validation logic, prefer an allowlist over a
  blocklist and enumerate every field a value can carry — promoted after
  this exact bug shape recurred four times in one function this slice.
- A pre-existing, unrelated test
  (`test_llm_description_setup.py::test_requirements_gains_no_other_new_dependencies`)
  hardcoded a dependency allow-list from an earlier slice and broke when
  `sqlglot` was added; per explicit user decision, its allow-list was
  extended (not weakened) with a comment explaining why.
- 91 tests pass (`python -m unittest discover tests`, via the project
  `.venv`) — 86 from prior slices (minus 6 deleted `CheckReferencesTests`,
  plus net-new coverage) + `ValidateSqlTests`' 11 cases covering the
  positive fixed-question SQL and every bug found above.

## Proof
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

## Open questions / known issues
- Test runner: still `unittest`, still via the project `.venv`. The next
  slice adds `asyncpg`, which is inherently async — plain `unittest`
  supports this natively via `unittest.IsolatedAsyncioTestCase` (stdlib,
  no new test dependency needed), so this doesn't force the long-carried
  "move to pytest" decision yet; flag if that changes.
- Lint/type tooling (`ruff`, `mypy`) named in CLAUDE.md's Commands still
  aren't installed in the project `.venv` — carried over, not blocking.
- `fetch_catalog_schema(cur)` issues two fresh queries against the
  catalog on every single `validate_sql()` call, no caching — fine at
  current CLI scale (one call per run), revisit only if this becomes a
  real latency concern once M4's API wraps this pipeline.
- `validate_sql` checks that every referenced identifier *exists*; it
  does not check semantic correctness (e.g. a join that's technically
  valid SQL but wrong business logic) — that's the LLM's job and the
  eval's job, not this validation layer's, per ARCHITECT.md's layering.

## Next slice (the brief, written NOW while context is hot)
Goal:
Execute the validated SQL for real against a new read-only `asyncpg`
connection (using the already-provisioned `OLIST_RO_USER`/
`OLIST_RO_PASSWORD`), with a hard `LIMIT 1000` cap and a 10s
`statement_timeout` injected first — ARCHITECT.md's defense-in-depth
layer 3 — and print the fixed question's actual result rows. This
completes M2 Pipeline v0's full chain (question → SQL → validate →
execute → printed answer) for the one fixed question.

Constraints:
New dependency, pre-approved by ARCHITECT.md's own wording ("a separate
asyncpg pool with a SELECT-only user exclusively for generated SQL") —
`asyncpg` only, pinned in `requirements.txt` to whatever version `pip
install` resolves, confirmed at Gate 1. The asyncpg connection MUST use
`OLIST_RO_USER`/`OLIST_RO_PASSWORD` (never `POSTGRES_USER`/
`POSTGRES_PASSWORD`) — blast-radius isolation via the read-only grant is
the product's core safety property (ARCHITECT.md), reusing
`POSTGRES_HOST`/`POSTGRES_PORT`/`POSTGRES_DB` for the rest of the
connection params. Before executing, inject a `LIMIT 1000` cap — only if
the SQL has no `LIMIT` or a looser one than 1000, never loosen an
existing tighter `LIMIT` (the fixed question's `LIMIT 5` must survive
untouched) — reusing sqlglot (already a dependency) to modify the parsed
statement rather than string-munging SQL text. Set `statement_timeout`
to 10s scoped to just this query (e.g. `SET LOCAL statement_timeout` inside
an explicit transaction), not a global/session-wide setting. A full
persistent connection pool (`asyncpg.create_pool` reused across many
requests) is the eventual FastAPI shape (M4) — for this CLI-only slice, a
single connection opened and closed per run is sufficient; don't build
pool lifecycle management prematurely. Still only the one
`FIXED_QUESTION` from `generate_sql.py` — no arbitrary/multi-question
support. No chart or natural-language explanation step (`analyze.md`,
later milestone) — "printed answer" means the raw result rows.

Inputs:
ARCHITECT.md's defense-in-depth layer 3 (LIMIT 1000 + statement_timeout
10s) and two-pool/blast-radius-isolation decision; PLAN.md's M2
definition; `app/pipeline/generate_sql.py`'s `generate_sql()` and
`app/pipeline/validate_sql.py`'s `validate_sql(sql, cur)` as the two
already-built upstream steps; `.env.example`'s `OLIST_RO_USER`/
`OLIST_RO_PASSWORD` (provisioned by M1's seed, already granted
SELECT-only per `tests/test_olist_ro_permissions.py`); this session's
proof output (5 rows, strictly descending) as the sanity-check reference
for the new done-check.

Outputs:
- `requirements.txt` gains `asyncpg` (pinned).
- A new module (exact path proposed at Gate 1, e.g.
  `app/pipeline/execute_sql.py`) exporting an async `execute_sql(sql)` (or
  similar): opens an `OLIST_RO_USER` asyncpg connection, injects the
  LIMIT cap via sqlglot, sets the scoped statement_timeout, executes,
  returns the result rows, closes the connection.
- A new end-to-end runner + done-check (exact names proposed at Gate 1,
  e.g. `app/pipeline/answer.py` + `app/pipeline/verify_answer.py`)
  chaining `generate_sql()` → `validate_sql()` → `execute_sql()` and
  printing the fixed question's real answer rows.
- Tests: the LIMIT-injection logic's three cases (no `LIMIT` → 1000
  added; looser `LIMIT` → capped to 1000; tighter `LIMIT` → left
  untouched) tested directly against the pure sqlglot-modification logic;
  a real end-to-end test that runs the new CLI and confirms actual rows
  come back through the `OLIST_RO_USER` role (proving the read-only path
  is real, not asserted).

Done-check:
`python -m app.pipeline.verify_answer` (or whatever name Gate 1 confirms)
exits 0 and prints the fixed question's real result rows, executed via
the read-only asyncpg connection — paste its output. Separately, a test
run demonstrates all three LIMIT-injection cases behave as specified
above.

Out-of-scope:
The `analyze.md` chart/explanation step, the repair loop, the business
glossary (F5/M3), retrieval/pgvector (M3), FastAPI/frontend (M4/M5), CI,
persistent connection pooling reused across multiple requests, arbitrary/
multi-question CLI support, changing `generate_sql.py`'s or
`validate_sql.py`'s existing behavior.
