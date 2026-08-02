# Brief — execute-sql

Date: 2026-08-02
Milestone: M2 Pipeline v0 in the CLI (question → SQL → validate → execute → printed answer)

Goal:
Execute the validated SQL for the fixed question against a new read-only
`asyncpg` connection and print the real result rows, completing M2's full
pipeline chain for that one question.

Constraints:
New dependency `asyncpg` only, pinned in `requirements.txt` to whatever
version `pip install` resolves — pre-approved by ARCHITECT.md's own
wording ("a separate asyncpg pool with a SELECT-only user exclusively for
generated SQL"); confirmed again at Gate 1. The asyncpg connection MUST
authenticate as `OLIST_RO_USER`/`OLIST_RO_PASSWORD` (never
`POSTGRES_USER`/`POSTGRES_PASSWORD`) — blast-radius isolation via the
read-only grant is the product's core safety property (ARCHITECT.md),
reusing `POSTGRES_HOST`/`POSTGRES_PORT`/`POSTGRES_DB` for the rest of the
connection params. Before executing, inject a `LIMIT 1000` cap using
sqlglot (already a dependency) to modify the parsed statement — never
string-munging SQL text — only if the SQL has no `LIMIT` or a looser one
than 1000; never loosen an existing tighter `LIMIT` (the fixed question's
`LIMIT 5` must survive untouched). Set `statement_timeout` to 10s scoped
to just this query (e.g. `SET LOCAL statement_timeout` inside an explicit
transaction), not a global/session-wide setting — this is ARCHITECT.md's
defense-in-depth layer 3 (LIMIT + timeout), with read-only grants as the
last line of defense, never the only one. A single connection opened and
closed per run is sufficient for this CLI-only slice — no
`asyncpg.create_pool` / pool lifecycle management (that's M4's FastAPI
shape). Still only the one `FIXED_QUESTION` from `generate_sql.py` — no
arbitrary/multi-question support.

Inputs:
`app/pipeline/generate_sql.py`'s `generate_sql()` and
`app/pipeline/validate_sql.py`'s `validate_sql(sql, cur)` as the two
already-built upstream steps; ARCHITECT.md's defense-in-depth layer 3 and
two-pool/blast-radius-isolation decision; `.env.example`'s
`OLIST_RO_USER`/`OLIST_RO_PASSWORD` (provisioned by M1's seed, already
granted SELECT-only per `tests/test_olist_ro_permissions.py`);
`app/catalog/sync.py`'s `connect()` as the existing pattern for reading
required env vars (`require_env`), for parity in the new asyncpg
connection helper; this session's proof output from the validate-sql
slice (5 rows, strictly descending) as the sanity-check reference for the
new done-check.

Outputs:
- `requirements.txt` gains `asyncpg` (pinned).
- A new module (exact path proposed at Gate 1, e.g.
  `app/pipeline/execute_sql.py`) exporting an async `execute_sql(sql)` (or
  similar): opens an `OLIST_RO_USER` asyncpg connection, injects the LIMIT
  cap via sqlglot, sets the scoped statement_timeout, executes, returns
  the result rows, closes the connection.
- A new end-to-end runner + done-check (exact names proposed at Gate 1,
  e.g. `app/pipeline/answer.py` + `app/pipeline/verify_answer.py`)
  chaining `generate_sql()` → `validate_sql()` → `execute_sql()` and
  printing the fixed question's real answer rows.
- Tests: the LIMIT-injection logic's three cases (no `LIMIT` → 1000
  added; looser `LIMIT` → capped to 1000; tighter `LIMIT` → left
  untouched) tested directly against the pure sqlglot-modification logic;
  a real end-to-end test (via `unittest.IsolatedAsyncioTestCase`, stdlib,
  no new test dependency) that runs the new CLI path and confirms actual
  rows come back through the `OLIST_RO_USER` role.

Done-check:
`python -m app.pipeline.verify_answer` (or whatever name Gate 1 confirms)
exits 0 and prints the fixed question's real result rows, executed via
the read-only asyncpg connection — paste its output. Separately,
`python -m unittest discover tests` passes, demonstrating all three
LIMIT-injection cases plus the full existing suite green.

Out-of-scope:
The `analyze.md` chart/explanation step, the repair loop, the business
glossary (F5/M3), retrieval/pgvector (M3), FastAPI/frontend (M4/M5), CI,
persistent connection pooling reused across multiple requests, arbitrary/
multi-question CLI support, changing `generate_sql.py`'s or
`validate_sql.py`'s existing behavior.
