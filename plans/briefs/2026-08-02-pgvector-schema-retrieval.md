# Brief — pgvector schema retrieval

Date: 2026-08-02
Milestone: M3 Retrieval + repair + evals (first link: schema retrieval)

Goal:
For the fixed question, `generate_sql()`'s schema context comes from a
pgvector top-k similarity search over embedded table descriptions instead
of every table's full context.

Constraints:
New dependency `voyageai` (pinned in `requirements.txt` to whatever `pip
install` resolves), per ARCHITECT.md's amendment naming Voyage AI as the
embeddings provider — model name and output dimension confirmed at Gate 1.
New env var `VOYAGE_API_KEY` in `.env.example` (and `.env`, gitignored).
Embeddings stored in a new `app`-schema table using the pgvector extension
already installed by M1's seed (`CREATE EXTENSION IF NOT EXISTS vector` in
`scripts/seed.py`) — no new vector store, per ARCHITECT.md's "one
PostgreSQL instance, three concerns" decision. Embed the exact same
per-table `description` text `app/catalog/describe.py` already generates
and stores in `app.catalog_tables` — no new text source, no duplicate
description-generation logic. Retrieval is a top-k pgvector cosine-distance
(`<=>`) query against the fixed question's own embedding (k proposed at
Gate 1 — only 9 olist tables exist total, so k should be small, e.g. 3-5).
`generate_sql.py`'s `build_schema_context()` is explicitly in scope to
change (unlike every prior slice, which forbade touching
`generate_sql.py`). Still only the one `FIXED_QUESTION` — no
arbitrary-question CLI support yet. No re-embedding staleness/cache-
invalidation logic beyond what `sync.py`/`describe.py` already do —
embedding runs once via a new idempotent script mirroring their upsert
pattern, not on every `generate_sql()` call.

Inputs:
ARCHITECT.md's amended embeddings-provider decision (Voyage AI) and its
pgvector/one-postgres-instance decision; `app/catalog/describe.py`'s
existing table descriptions (already live in
`app.catalog_tables.description`); `app/pipeline/generate_sql.py`'s
`build_schema_context()` and `FIXED_QUESTION`; `.env.example`; `scripts/
seed.py`'s existing `CREATE EXTENSION IF NOT EXISTS vector`.

Outputs:
- `requirements.txt` gains `voyageai` (pinned); `.env.example` gains
  `VOYAGE_API_KEY`.
- New DDL: an `app`-schema table storing one embedding vector per catalog
  table (exact name/shape proposed at Gate 1, e.g.
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
  never a hardcoded full-table-list check); the embed script is
  idempotent across two runs (mirroring `test_catalog_sync.py`'s/
  `test_seed_idempotency.py`'s pattern).

Done-check:
`python -m app.pipeline.verify_generate_sql` still exits 0 and produces
the same-shaped correct SQL for the fixed question, now sourced from
retrieved (not full) schema context — paste output. Separately, a test
run demonstrates retrieval returns a real top-k subset (fewer than all 9
tables) containing the tables the fixed question needs.

Out-of-scope:
Business glossary retrieval (F5, a later M3 slice), the one-shot repair
loop, the eval harness (`evals/questions.yaml`, a later M3 slice),
FastAPI/frontend (M4/M5), CI, arbitrary/multi-question support beyond
`FIXED_QUESTION`, changing `validate_sql.py`/`execute_sql.py`/
`answer.py`/`verify_answer.py`'s existing behavior, re-embedding
staleness/cache-invalidation logic.
