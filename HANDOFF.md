# Handoff

Date: 2026-08-02
Slice just completed: plans/briefs/2026-08-02-pgvector-schema-retrieval.md +
  plans/logs/2026-08-02-pgvector-schema-retrieval.md (commit 92c76d9)

## State of the work
- **M3's first retrieval link is complete**: `generate_sql()`'s schema
  context now comes from a pgvector top-k similarity search over embedded
  table descriptions, not the full 9-table catalog.
- `app/catalog/embed.py` — new module: `SCHEMA_DDL` (creates
  `app.catalog_embeddings(table_id INTEGER PRIMARY KEY REFERENCES
  app.catalog_tables(id), embedding vector(1024) NOT NULL)`, plus
  `CREATE EXTENSION IF NOT EXISTS vector` defensively), `VOYAGE_MODEL =
  "voyage-3.5"`, `EMBEDDING_DIMENSION = 1024`, `to_vector_literal(embedding)`
  (formats a float list as a pgvector text literal — no `pgvector` python
  package needed, values move through psycopg2 as `%s::vector`-cast text),
  `embed_text(client, model, text, input_type)` (wraps
  `client.embed(...)`, with a bounded rate-limit retry: 4 attempts, 20s
  apart, specifically for `voyageai.error.RateLimitError` — added mid-slice
  after the real dev Voyage account, on its free tier's 3 RPM cap, tripped
  during both a manual bulk-embed run and the full test suite), and
  `embed()` (loops `describe.fetch_tables(cur)`, skips any table already in
  `catalog_embeddings`, raises if `description is None`, embeds with
  `input_type="document"`, upserts, commits per-row — deliberately unlike
  `sync.py`'s single final commit, since embedding is a billed call and a
  mid-run crash shouldn't force re-embedding already-paid-for tables).
- `app/catalog/verify_embed.py` — new done-check CLI (added beyond the
  brief's literal done-check, for consistency with `sync`/`describe`'s
  paired-verify-script convention; flagged explicitly at Gate 1).
- `app/pipeline/generate_sql.py` — new `retrieve_relevant_tables(cur,
  voyage_client, question, k=RETRIEVAL_K)` (`RETRIEVAL_K = 5`): embeds
  `question` with `input_type="query"`, runs `ORDER BY ce.embedding <=>
  %s::vector LIMIT %s` joining `catalog_embeddings` to `catalog_tables`.
  `build_schema_context(cur, tables)`'s signature changed — takes a
  pre-fetched rows list instead of calling `fetch_tables(cur)` itself, so
  it works for any subset. `generate_sql()` now builds a `voyageai.Client`
  alongside the existing Anthropic client and calls
  `retrieve_relevant_tables()` then `build_schema_context()`.
- `requirements.txt` gained `voyageai==0.5.0` (pinned; ARCHITECT.md's own
  Voyage AI amendment pre-approved it). `.env.example` gained
  `VOYAGE_API_KEY`; the real `.env` has a working key.
- The no-slop-reviewer pass (two rounds) found one issue: `embed_text()`'s
  new rate-limit retry logic had zero test coverage. Fixed with
  `EmbedTextRateLimitRetryTests` in `tests/test_catalog_embed.py` — fake
  Voyage client stand-ins + patched `time.sleep`, runs in 0.001s, no real
  network. Second round confirmed clean.
- `tests/test_generate_sql_cli.py`'s pre-existing
  `test_build_schema_context_covers_all_nine_tables` (which asserted the
  old full-catalog behavior) was rewritten to assert a genuine top-k
  subset instead, per the brief's explicit "never hardcode the full table
  list" instruction — confirms `order_items`/`products` are retrieved and
  the set is smaller than all 9.
- `tests/test_llm_description_setup.py`'s dependency allowlist and
  `tests/test_env_example.py`'s `REQUIRED_VARS` both extended for
  `voyageai`/`VOYAGE_API_KEY` (same precedent as `sqlglot`/`asyncpg`/
  `ANTHROPIC_API_KEY` in prior slices).
- `evals/generate_sql.md` extended with a second case: the same fixed
  question under retrieved (not full-catalog) context produces
  structurally identical SQL — retrieval didn't regress quality for this
  one question (still a smoke check, not statistical confidence).
- 113 tests pass (`python -m unittest discover tests`, via the project
  `.venv`) — 111 from prior slices (2 net removed/rewritten as one) + 9
  new (4 in `test_catalog_embed.py`'s CLI class + 2 in its new
  rate-limit-retry unit test class + 3 in `test_verify_embed_script.py`).
- All 9 olist tables are embedded in the real dev database right now
  (`python -m app.catalog.verify_embed` passes).

## Proof
```
$ python -m app.catalog.verify_embed
Embeddings:
  [OK] olist.customers: embedding=1024 dims
  [OK] olist.geolocation: embedding=1024 dims
  [OK] olist.order_items: embedding=1024 dims
  [OK] olist.order_payments: embedding=1024 dims
  [OK] olist.order_reviews: embedding=1024 dims
  [OK] olist.orders: embedding=1024 dims
  [OK] olist.product_category_name_translation: embedding=1024 dims
  [OK] olist.products: embedding=1024 dims
  [OK] olist.sellers: embedding=1024 dims

verify_embed: PASSED

$ python -m app.pipeline.verify_generate_sql
Generated SQL:
SELECT p.product_category_name, COUNT(DISTINCT oi.order_id) AS number_of_orders FROM olist.order_items oi JOIN olist.products p ON oi.product_id = p.product_id GROUP BY p.product_category_name ORDER BY number_of_orders DESC LIMIT 5

verify_generate_sql: PASSED

$ python -m unittest discover tests
.................................................................................................................
----------------------------------------------------------------------
Ran 113 tests in 173.223s

OK
```

## Open questions / known issues
- **Voyage's free-tier 3 RPM rate limit is real and will recur.** Any
  future slice adding a Voyage call (e.g. F5 glossary retrieval) will hit
  the same ceiling. `embed_text()`'s retry-with-backoff is the pattern to
  reuse, not reinvent. First occurrence this slice — not yet promoted to
  a standing CLAUDE.md rule (ratchet threshold is second repetition).
- **`generate_sql()`/`get_answer()` are still hardcoded to
  `FIXED_QUESTION`** — no arbitrary-question support anywhere in the
  pipeline yet. The next slice (below) needs to change this minimally
  (an optional `question` parameter, default `FIXED_QUESTION`, zero
  behavior change to existing CLI/verify scripts) to run more than one
  question through the pipeline at all.
- **No PyYAML dependency yet.** `evals/questions.yaml` (named in
  CLAUDE.md's Commands and PRD.md §10) needs a YAML parser; `voyageai`
  pulled in `pyyaml` transitively this slice, but it isn't pinned as an
  explicit top-level dependency the way every other import in this
  codebase is. Needs asking/confirming at next Gate 1 per CLAUDE.md's "no
  new dependencies without asking" rule — flagging now, not deciding now.
- PRD.md §10 specifies an eventual 30-question eval set and an ≥80%
  ship-gate target — both are M8 concerns. This project's own
  `templates/eval.md` says "start with 5"; the next slice below starts
  there deliberately, not at 30.
- Lint/type tooling (`ruff`, `mypy`) and the test runner (`unittest`, not
  `pytest`) remain unaddressed, carried over from every prior slice —
  still not blocking.

## Next slice (the brief, written NOW while context is hot)
Goal:
A working eval harness — `evals/questions.yaml` + `python -m evals.run`
— runs a small set of curated real-world questions through the real,
already-built pipeline (`generate_sql` → `validate_sql` → `execute_sql`,
via `answer.get_answer()`) and reports a per-question pass/fail plus an
overall accuracy score.

Constraints:
Start with exactly 5 curated questions (per `templates/eval.md`'s own
"start with 5" guidance and PRD.md §10's eventual 30 being an M8, not
M3, target) — each needs a real expected-result assertion (e.g. a
specific top value, a specific count), hand-verified against the real
`olist` database during this slice, not invented. To run more than the
one `FIXED_QUESTION`, `generate_sql()` and `answer.get_answer()` both
need an optional `question` parameter defaulting to `FIXED_QUESTION` —
every existing CLI (`python -m app.pipeline.generate_sql`, `python -m
app.pipeline.answer`) and both verify scripts must keep their exact
current behavior with zero code changes on their end, proven by the
full existing test suite passing unchanged. `validate_sql.py`/
`execute_sql.py` need no changes — they already operate on a raw SQL
string, not a question. Grading is exact-match or code-assertion only
(no LLM-as-judge) — same threshold `evals/generate_sql.md`/
`evals/table_description.md` already established (revisit once the set
grows past what's easy to read by hand). New dependency: `PyYAML`, to
parse `evals/questions.yaml` — confirm at Gate 1 (already pulled in
transitively by `voyageai`, but needs its own explicit pin like every
other dependency in `requirements.txt`).

Inputs:
PRD.md §10 (the eval spec: `evals/questions.yaml`, accuracy scoring,
eventual 30-question/≥80% targets); `templates/eval.md` (the case-table
shape); `evals/generate_sql.md` and `evals/table_description.md` (this
project's existing per-slice eval-log precedent, including the
LLM-as-judge deferral threshold); `app/pipeline/answer.py`'s
`get_answer()`; `app/pipeline/generate_sql.py`'s `generate_sql()` and
`FIXED_QUESTION`; the real `olist` schema (for hand-verifying the 5
questions' expected assertions).

Outputs:
- `requirements.txt` gains `PyYAML` (pinned, pending Gate 1 confirmation).
- `evals/questions.yaml` — 5 curated questions, each with an expected
  assertion checkable in code (e.g. `{question: "...", expected: {top_row:
  ["beleza_saude", 8836]}}` or similar — exact shape proposed at Gate 1).
- `evals/run.py` (+ `evals/__init__.py` if needed for `python -m
  evals.run` to work as a package) — loads `questions.yaml`, calls
  `answer.get_answer(question)` per question, checks the result against
  its expected assertion, prints a per-question PASS/FAIL line and a
  final "N/5 correct" summary.
- `generate_sql()` and `get_answer()` gain an optional `question`
  parameter (default `FIXED_QUESTION`) threaded through
  `retrieve_relevant_tables()`/`build_schema_context()`/`call_llm_for_sql()`
  — no other behavior change.
- Tests: the parameterization doesn't change `FIXED_QUESTION`'s default
  behavior (full existing suite passes unchanged); the eval runner
  correctly reports pass/fail against a known-good and a known-bad
  fixture case.

Done-check:
`python -m evals.run` exits 0 and prints a real accuracy score (e.g.
"5/5 correct" or honestly fewer) for the 5 curated questions — paste
output. Separately, `python -m unittest discover tests` still passes in
full, proving the `question` parameter change didn't alter any existing
CLI's default behavior — paste output.

Out-of-scope:
Reaching PRD's eventual 30-question set or its ≥80% ship-gate
enforcement (M8), the one-shot repair loop, business glossary retrieval
(F5), any new CLI flag for end-user-supplied arbitrary questions in a
production surface (M4/M5), changes to `validate_sql.py`/
`execute_sql.py` internals, LLM-as-judge grading, FastAPI/frontend, CI.
