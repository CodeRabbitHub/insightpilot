# Brief — business glossary retrieval

Date: 2026-08-03
Milestone: M3 Retrieval + repair + evals (second link: glossary retrieval,
after schema retrieval)

Goal:
For the fixed question (and every `evals/questions.yaml` question),
`generate_sql()`'s prompt context includes top-k relevant business-glossary
entries (KPI definitions), retrieved via pgvector alongside the existing
top-k schema context, with no regression in `evals/run.py`'s current 5/5
score.

Constraints:
New file `glossary.md` at the repo root: ~15 KPI definitions per PRD.md F5
(Revenue, AOV, Repeat purchase rate, Delivery time, Review score, Churn
proxy, etc.), each with an exact formula referencing real `olist` columns —
verified against the live schema, not invented. Reuse the exact same Voyage
AI embeddings provider, `voyage-3.5` model, and `embed_text()`'s existing
rate-limit retry-with-backoff (`app/catalog/embed.py`) — no new provider,
no reinvented retry logic. New `app`-schema table for glossary chunk
embeddings, one row per KPI definition — name `app.kb_chunks`, per PRD.md's
own Data Model section (`kb_chunks (id, source, content, embedding
vector(1536))`) and per `test_describe_cli.py`'s explicit reservation of
that name for M3. Vector dimension is `1024`, not the PRD's `1536` — that
number predates the Voyage AI amendment and Voyage's real, already-proven
output size (`app/catalog/embed.py`'s `EMBEDDING_DIMENSION = 1024`);
`content` holds the KPI definition chunk text, `source` holds a stable
identifier for the KPI (e.g. its heading/slug from `glossary.md`). New
idempotent embed script mirroring `app/catalog/embed.py`'s exact
convention (skip already-embedded chunks, commit per-row, its own
`verify_*` CLI) — proposed location `app/glossary/embed.py` +
`app/glossary/verify_embed.py`, a new package mirroring `app/catalog/`'s
shape since this is a new concern (glossary), not catalog. `generate_sql.py`
gains `retrieve_relevant_glossary_entries(cur, voyage_client, question,
k=...)`, analogous to the existing `retrieve_relevant_tables()`, called
with the same `question` parameter already threaded through
`generate_sql()`. `prompts/generate_sql.md` gains a glossary-context
placeholder (a real templated section via `string.Template`, not a
hardcoded string). Per CLAUDE.md's binding rule, a prompt change without an
eval run is not done — `evals/run.py` must be re-run after this change and
its score reported, even if unchanged from 5/5. No new dependencies
expected (reuses `voyageai`, already pinned).

Inputs:
PRD.md's F5 section (glossary spec) and its Data Model section (`kb_chunks`
shape); ARCHITECT.md (Voyage AI + pgvector decisions); `app/catalog/embed.py`
(the exact pattern to mirror: `SCHEMA_DDL`, `to_vector_literal`,
`embed_text`, idempotent `embed()`); `test_describe_cli.py`'s `kb_chunks`
reservation test; `app/pipeline/generate_sql.py`'s
`retrieve_relevant_tables()` / `build_schema_context()` / `build_prompt()`
/ `generate_sql()`; `prompts/generate_sql.md`; `evals/questions.yaml` +
`evals/run.py` (used to prove glossary retrieval doesn't regress accuracy).

Outputs:
- `glossary.md` — ~15 KPI definitions with real `olist` column references.
- New DDL: `app.kb_chunks(id, source, content, embedding vector(1024))`.
- `app/glossary/embed.py` + `app/glossary/verify_embed.py` — idempotent
  embed script + verify CLI, mirroring `app/catalog/embed.py`'s convention.
- `generate_sql.py` gains `retrieve_relevant_glossary_entries()` + glossary
  context building, called alongside the existing schema retrieval inside
  `generate_sql()`, using the same `question`.
- `prompts/generate_sql.md` extended with a real glossary-context section.
- Tests: glossary retrieval returns a genuine top-k subset (never a
  hardcoded full-list check, mirroring the schema-retrieval slice's own
  test precedent); the new embed script is idempotent across two runs.
- `evals/run.py`'s score re-reported after the prompt change.

Done-check:
`python -m evals.run` exits 0 and reports its score after the glossary
context is added — paste output, and confirm it's not a regression from
the current 5/5. Separately, `python -m unittest discover tests` passes in
full — paste output (expect ~15-20 min real runtime, per CLAUDE.md; not
hung).

Out-of-scope:
Document upload/parsing UI (F5 explicitly excludes this — glossary is
seeded, not uploaded); the one-shot repair loop (a separate remaining M3
slice); changing `retrieve_relevant_tables()`/schema retrieval's own
behavior; `validate_sql.py`/`execute_sql.py` internals; FastAPI/frontend;
CI; fixing the deeper stop_verify.py/shared-DB-test concurrency hazard
noted in HANDOFF.md (a real, separate, dedicated slice of its own).
