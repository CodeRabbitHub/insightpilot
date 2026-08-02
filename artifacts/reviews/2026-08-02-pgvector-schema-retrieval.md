# Review gate — pgvector schema retrieval

Date: 2026-08-02
Brief: plans/briefs/2026-08-02-pgvector-schema-retrieval.md
Diff reviewed: working tree (uncommitted), against HEAD (ce458f5)

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review

`git diff --stat` (tracked files) + new untracked files:

```
 .env.example                        |   1 +
 app/pipeline/generate_sql.py        |  28 ++++++++--
 requirements.txt                    |   1 +
 tests/test_env_example.py           |   5 ++
 tests/test_generate_sql_cli.py      | 100 ++++++++++++++++++++++++++--------
 tests/test_llm_description_setup.py |   5 ++
 7 files changed, 139 insertions(+), 26 deletions(-)

 app/catalog/embed.py                 (new, 117 lines)
 app/catalog/verify_embed.py          (new,  51 lines)
 tests/_embed_helpers.py              (new,  63 lines)
 tests/test_catalog_embed.py          (new, 234 lines)
 tests/test_verify_embed_script.py    (new, 126 lines)
```

(`plans/logs/_auto-capture.md` also shows modified in `git status` — that's
the hook-appended record of the *previous* slice's commit, not part of
this diff; not reviewed as part of this gate.)

~730 lines total across 12 files, comparable to the prior execute-sql
slice (778 insertions). Every line was read (directly and via two
no-slop-reviewer passes). PASS.

## 2. The stated goal matches the actual change

**Brief's Goal:** For the fixed question, `generate_sql()`'s schema
context comes from a pgvector top-k similarity search over embedded
table descriptions instead of every table's full context.

**What the diff does:** Adds `app/catalog/embed.py` (embeds each
`app.catalog_tables.description` via Voyage AI, upserts into a new
`app.catalog_embeddings` pgvector table, idempotent/skip-if-done) +
`app/catalog/verify_embed.py` (done-check CLI, consistent with the
sync/describe convention). Changes `generate_sql.py`: new
`retrieve_relevant_tables()` embeds the fixed question and runs a
pgvector top-k query; `build_schema_context()`'s signature changes to
take a pre-fetched table list instead of the full catalog;
`generate_sql()` wires retrieval in before context-building. Adds
`voyageai` to `requirements.txt`, `VOYAGE_API_KEY` to `.env.example`.
Tests added/updated accordingly, including the one pre-existing test
that asserted "all 9 tables" — rewritten to assert a genuine top-k
subset instead, per the brief's explicit anti-hardcoding instruction.

Matches exactly. No missing behavior, no unrequested extras beyond
`verify_embed.py`, which was proposed and flagged explicitly at the plan
stage (Gate 1) as a consistency addition beyond the literal done-check,
not smuggled in. PASS.

## 3. The eval or test passed

Done-check, run fresh:
```
$ python -m app.pipeline.verify_generate_sql
Generated SQL:
SELECT p.product_category_name, COUNT(DISTINCT oi.order_id) AS number_of_orders FROM olist.order_items oi JOIN olist.products p ON oi.product_id = p.product_id GROUP BY p.product_category_name ORDER BY number_of_orders DESC LIMIT 5

verify_generate_sql: PASSED
```

Retrieval subset demonstration (the brief's second done-check clause):
```
$ python -m unittest tests.test_generate_sql_cli.GenerateSqlEndToEndTests.test_retrieve_relevant_tables_returns_a_real_subset_not_the_full_catalog
Ran 1 test in 5.564s
OK
```
(Manually confirmed the actual retrieved set for the fixed question:
`products, product_category_name_translation, orders, order_reviews,
order_items` — 5 of 9 tables, includes `order_items`/`products`.)

Full suite, run fresh:
```
$ python -m unittest discover tests
.................................................................................................................
----------------------------------------------------------------------
Ran 113 tests in 173.223s

OK
```
PASS.

## 4. The no-slop review found no unresolved issues

Two no-slop-reviewer passes (read-only subagent):

- **First pass** found one finding: `embed_text()`'s bounded rate-limit
  retry/backoff (added after this session's real Voyage account tripped
  its 3 RPM free-tier limit during the first full-suite run) had zero
  test coverage. **Fixed**: added `EmbedTextRateLimitRetryTests` to
  `tests/test_catalog_embed.py` — two pure unit tests using fake Voyage
  client stand-ins and a patched `time.sleep`, proving both the recovery
  path and the exhausted-attempts failure path, in 0.001s with no real
  network calls.
- **Second pass** (against the final diff, including the fix) confirmed
  the finding resolved and the new test code sound (fakes correctly
  mirror the real `voyageai.Client.embed()` interface, verified against
  the installed package source). Two low-severity/informational notes,
  neither requiring a code change:
  - `build_schema_context()`'s `description is None` guard is now
    effectively unreachable in the happy path (an embedded table is
    guaranteed already-described, since `embed.py` refuses to embed a
    `None` description). Reviewed and kept as-is: still reachable
    against a manually-corrupted DB row, same defensive shape as other
    guards in this codebase, and removing it would trade a harmless
    safety net for no real benefit.
  - `plans/logs/_auto-capture.md`'s pending modification is unrelated to
    this slice (confirmed above).

No unresolved findings remain. PASS.

## 5. The shipping proof is attached

Real commands against the real dev Postgres + real Voyage/Anthropic
APIs (not just the test suite):

```
$ python -m app.catalog.embed
  olist.customers: already embedded, skipping
  ... (all 9 already embedded, skipping)
Embedding sync complete.

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
```
PASS.

## Rejected or changed

- **Changed**: `embed_text()`'s rate-limit handling. The plan didn't
  originally call for retry/backoff — it was added mid-build after a
  real failure (the full test suite hit Voyage's 3 RPM free-tier limit
  across ~7 cumulative calls within one run, causing 4 pre-existing
  subprocess-based tests to fail). Fixed at the code level (bounded
  retry with a real wait for the rate window to clear) rather than by
  touching the failing tests, per CLAUDE.md's standing rule against
  weakening tests to make them pass.
- **Changed**: added a dedicated pure-unit-test class for that same
  retry logic after the first no-slop pass flagged it as untested —
  not part of the original test-writer output.
- **Kept as-is (considered, not changed)**: `build_schema_context()`'s
  now-defensive-only `description is None` check, per check 4 above.

## Verdict

**accept** — all five checks green.
