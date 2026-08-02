# Slice log — pgvector schema retrieval

Date: 2026-08-02
Brief: plans/briefs/2026-08-02-pgvector-schema-retrieval.md

## The plan you approved
Embed each catalog table's existing LLM description via Voyage AI
(`voyage-3.5`, 1024-dim) into a new `app.catalog_embeddings` pgvector
table via a new idempotent `app/catalog/embed.py` (+ `verify_embed.py`,
mirroring `sync.py`/`describe.py`'s established shape). At generate
time, embed the fixed question and run a pgvector top-k (k=5) query to
build `generate_sql.py`'s schema context, replacing the full-catalog
context it used before. Vector values move through plain psycopg2 as
`::vector`-cast text literals — no new `pgvector` python dependency,
only `voyageai` (the brief's one authorized new dependency).

## The diff you accepted
Commit `92c76d9` — "pgvector schema retrieval: swap generate_sql's
context from full catalog to top-k". Full stat in
`plans/logs/_auto-capture.md`'s matching entry. 13 files, 953
insertions: new `app/catalog/embed.py` + `verify_embed.py`,
`generate_sql.py`'s `build_schema_context()` signature change + new
`retrieve_relevant_tables()`, `requirements.txt`/`.env.example`
additions, and test coverage (new `tests/test_catalog_embed.py`,
`tests/test_verify_embed_script.py`, `tests/_embed_helpers.py`, plus
required edits to `tests/test_generate_sql_cli.py` — the pre-existing
"covers all nine tables" test rewritten to assert a genuine top-k
subset — and the dependency/env-var allowlist extensions in
`tests/test_llm_description_setup.py`/`tests/test_env_example.py`).
Gate 2 record: `artifacts/reviews/2026-08-02-pgvector-schema-retrieval.md`.

## The done-check output
```
$ python -m app.pipeline.verify_generate_sql
Generated SQL:
SELECT p.product_category_name, COUNT(DISTINCT oi.order_id) AS number_of_orders FROM olist.order_items oi JOIN olist.products p ON oi.product_id = p.product_id GROUP BY p.product_category_name ORDER BY number_of_orders DESC LIMIT 5

verify_generate_sql: PASSED
```
Retrieval subset demonstration (brief's second done-check clause):
top-5 of 9 tables for the fixed question — `products`,
`product_category_name_translation`, `orders`, `order_reviews`,
`order_items` — includes `order_items`/`products`, proven by
`test_retrieve_relevant_tables_returns_a_real_subset_not_the_full_catalog`.
Full suite: `Ran 113 tests in 173.223s / OK`.

## One thing you rejected or changed
Mid-build, the real Voyage account (free tier, 3 RPM) tripped a genuine
rate limit — first while bulk-embedding all 9 tables by hand (needed 6
paced retries to finish), then again across the full test suite (4
pre-existing subprocess-based tests failed, since `generate_sql()` now
calls Voyage on every run, same as it's always called Anthropic).
Rather than touch the failing tests (forbidden — CLAUDE.md: never
weaken/skip a test to make it pass), I added a bounded retry-with-
backoff to `embed_text()` itself (`RATE_LIMIT_MAX_ATTEMPTS=4`,
20s between attempts) — the actual fix, not a workaround, since it waits
out the real rate window instead of masking it. The first no-slop pass
then caught that this new retry logic itself had zero test coverage, so
I added `EmbedTextRateLimitRetryTests` (fake Voyage client stand-ins +
patched `time.sleep`, 0.001s, no real network) before re-gating. This
wasn't in the approved plan; wasn't a rubber-stamp.

This is the first time this project has hit a real external rate limit
mid-build (checked prior slice logs — no precedent). Not promoting to a
standing rule yet per the ratchet's "second repetition" threshold, but
flagging: any future slice adding a Voyage call (e.g. F5 glossary
retrieval) will hit the same 3 RPM ceiling and should reuse
`embed_text()`'s retry rather than reinvent it.

## The next smallest slice
Build the eval harness (`evals/questions.yaml` + `python -m evals.run`,
already named in CLAUDE.md's Commands but not yet built) — gives M3 a
repeatable accuracy number before layering glossary retrieval or the
repair loop on top of the retrieval work this slice and the last one
landed.
