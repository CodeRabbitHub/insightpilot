# Handoff

Date: 2026-08-02
Slice just completed: plans/briefs/2026-08-02-execute-sql.md +
  plans/logs/2026-08-02-execute-sql.md (commit 8fa281f)

## State of the work
- **M2 Pipeline v0 is complete**: question → SQL → validate → execute →
  printed answer, fully proven end to end for the one fixed question.
- `app/pipeline/execute_sql.py` — new module exporting `cap_limit(sql,
  cap=1000)` (pure, no DB: edits the sqlglot-parsed statement's `Limit`
  node directly — adds a cap if none exists, tightens a looser one, never
  loosens a tighter one; raises `SqlValidationError` on a non-literal
  `LIMIT` expression it can't safely compare) and async `execute_sql(sql)`
  (opens one `asyncpg` connection authenticated as `OLIST_RO_USER`/
  `OLIST_RO_PASSWORD` — never the owner role — sets `SET LOCAL
  statement_timeout = '10s'` inside a transaction, executes the capped
  SQL, returns rows as `list[dict]`, always closes the connection).
- `app/pipeline/answer.py` — new module: `get_answer()` chains
  `generate_sql()` → (owner-role `connect()`/cursor) `validate_sql()` →
  `execute_sql()`, returning `(sql, rows)`; `print_answer(sql, rows)` is
  the shared presentation function reused by both `answer.main()` and
  `verify_answer.py` (extracted during Gate 2 to kill a duplicated print
  block).
- `app/pipeline/verify_answer.py` — new done-check CLI, same
  PASSED/FAILED/exit-code contract as `verify_generate_sql.py`.
- `requirements.txt` gained `asyncpg==0.31.0` (ARCHITECT.md's own
  two-pool/blast-radius-isolation wording pre-approved it, same precedent
  as `sqlglot` the slice before).
- The no-slop-reviewer pass found three issues, all fixed before Gate 2:
  an unhandled non-literal `LIMIT` expression in `cap_limit` (now fails
  closed with `SqlValidationError` + a regression test), a duplicated
  print block between `answer.py`/`verify_answer.py` (extracted to
  `print_answer()`), and a duplicated `DIALECT` constant in
  `execute_sql.py` (now imported from `validate_sql.py`, which it already
  imports `parse_single_select` from).
- `tests/test_llm_description_setup.py`'s hardcoded dependency allow-list
  extended again (same precedent as `sqlglot`) to include `asyncpg`.
- **ARCHITECT.md amended**: Voyage AI named as the embeddings provider
  (the "provider embeddings API for ~200 chunks" line was previously
  unpinned) — decided explicitly this session ahead of M3's retrieval
  work, which needs one picked.
- 104 tests pass (`python -m unittest discover tests`, via the project
  `.venv`) — 91 from prior slices + 13 new (6 pure `cap_limit` cases
  including a non-literal-LIMIT regression, 2 real-DB read-only-role
  integration tests, 1 statement_timeout-cancellation test, 3 CLI
  done-check tests, plus the extended dependency-allowlist assertion).

## Proof
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

## Open questions / known issues
- Test runner: still `unittest`, still via the project `.venv`. No new
  test dependency was needed this slice either
  (`unittest.IsolatedAsyncioTestCase` covered the async integration
  tests) — the long-carried "move to pytest" decision remains untouched.
- Lint/type tooling (`ruff`, `mypy`) named in CLAUDE.md's Commands still
  aren't installed in the project `.venv` — carried over again, not
  blocking.
- `execute_sql()` opens and closes a brand-new asyncpg connection on
  every call, no pooling — correct for this CLI-only slice per the
  brief's explicit constraint; M4's FastAPI shape is where
  `asyncpg.create_pool` lifecycle management actually belongs.
- Voyage AI was picked as the embeddings provider and amended into
  ARCHITECT.md this session, but no code against it exists yet — the
  `VOYAGE_API_KEY` env var, the `voyageai` dependency, and the embeddings
  storage table are all still to be built, starting with the next slice.

## Next slice (the brief, written NOW while context is hot)
Goal:
For the fixed question, `generate_sql()`'s schema context comes from a
pgvector top-k similarity search over embedded table descriptions instead
of every table's full context — the first working link of M3's retrieval
work.

Constraints:
New dependency `voyageai` (pinned in `requirements.txt` to whatever `pip
install` resolves), per this session's ARCHITECT.md amendment naming
Voyage AI as the embeddings provider — confirmed again at Gate 1. New
env var `VOYAGE_API_KEY` added to `.env.example` (and `.env`, gitignored).
Embeddings are stored in a new `app`-schema table using the pgvector
extension already installed by M1's seed (`CREATE EXTENSION IF NOT EXISTS
vector` already runs in `scripts/seed.py`) — no new vector store, per
ARCHITECT.md's "one PostgreSQL instance, three concerns" decision. Embed
the exact same per-table `description` text `app/catalog/describe.py`
already generates and stores in `app.catalog_tables` — no new text
source, no duplicate description-generation logic. Retrieval is a top-k
pgvector cosine-distance (`<=>`) query against the fixed question's own
embedding (k value proposed at Gate 1 — note only 9 olist tables exist
total, so k should be small, e.g. 3-5). `generate_sql.py`'s
`build_schema_context()` is now explicitly IN scope to change (unlike
every prior slice, which forbade touching `generate_sql.py`) — this
slice's whole point is changing how it sources context. Still only the
one `FIXED_QUESTION` — no arbitrary-question CLI support yet. No
re-embedding staleness/cache-invalidation logic beyond what `sync.py`/
`describe.py` already do — embedding runs once via a new idempotent
script (mirroring `sync.py`/`describe.py`'s upsert pattern), not on every
`generate_sql()` call.

Inputs:
ARCHITECT.md's amended embeddings-provider decision (Voyage AI) and its
pgvector/one-postgres-instance decision; `app/catalog/describe.py`'s
existing table descriptions (the text to embed, already live in
`app.catalog_tables.description`); `app/pipeline/generate_sql.py`'s
`build_schema_context()` (the function being changed) and
`FIXED_QUESTION`; `.env.example` (gains `VOYAGE_API_KEY`); `scripts/
seed.py`'s existing `CREATE EXTENSION IF NOT EXISTS vector` (pgvector is
already installed, not newly added this slice).

Outputs:
- `requirements.txt` gains `voyageai` (pinned); `.env.example` gains
  `VOYAGE_API_KEY`.
- New DDL: an `app`-schema table storing one embedding vector per
  catalog table (exact name/shape proposed at Gate 1, e.g.
  `app.catalog_embeddings(table_id, embedding vector(N))`).
- A new idempotent module/CLI (exact names at Gate 1, e.g.
  `app/catalog/embed.py` + `verify_embed.py`) that embeds every table's
  `description` via Voyage AI and upserts into the new table, mirroring
  `sync.py`/`describe.py`'s "safe to re-run" shape.
- `generate_sql.py`'s `build_schema_context()` (or a new function it
  calls) now embeds the fixed question, runs a pgvector top-k query
  against the new table, and builds context from only the retrieved
  tables — not every table in the catalog.
- Tests: retrieval returns a real, plausible top-k list for the fixed
  question (e.g. asserting `order_items`/`products` rank in the top-k,
  since the fixed question is about product categories and orders,
  never a hardcoded full-table-list check); the embed script is
  idempotent across two runs (mirroring `test_catalog_sync.py`'s/
  `test_seed_idempotency.py`'s pattern).

Done-check:
`python -m app.pipeline.verify_generate_sql` (unchanged command) still
exits 0 and produces the same-shaped correct SQL for the fixed question,
now sourced from retrieved (not full) schema context — paste output.
Separately, a test run demonstrates retrieval actually returns a
real top-k subset (fewer than all 9 tables) containing the tables the
fixed question needs.

Out-of-scope:
Business glossary retrieval (F5, a later M3 slice), the one-shot repair
loop, the eval harness (`evals/questions.yaml`, a later M3 slice),
FastAPI/frontend (M4/M5), CI, arbitrary/multi-question support beyond
`FIXED_QUESTION`, changing `validate_sql.py`/`execute_sql.py`/
`answer.py`/`verify_answer.py`'s existing behavior, re-embedding
staleness/cache-invalidation logic.
