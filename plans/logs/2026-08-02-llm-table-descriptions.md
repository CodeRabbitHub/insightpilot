# Slice log — LLM table descriptions

Date: 2026-08-02
Brief: plans/briefs/2026-08-02-llm-table-descriptions.md

## The plan you approved
For each of the 9 `catalog_tables` rows, call Claude once via the
`anthropic` SDK with context built from `ddl_summary` + `catalog_columns`,
validate the JSON reply with a Pydantic model (one retry), and persist
`description` — skipping any row already described. Required first
resolving `sync.py`'s TRUNCATE-wipes-descriptions conflict by switching to
an UPSERT on `table_name` (adding a `UNIQUE` constraint via an idempotent
migration block), with columns handled by a scoped `DELETE` + reinsert
instead of the old blanket truncate.

## The diff you accepted
Commit `a657fd6` — "LLM table descriptions: describe.py generates +
caches per-table Claude descriptions" (15 files changed, 1153
insertions(+), 19 deletions(-)). New: `app/catalog/describe.py`,
`app/catalog/verify_describe.py`, `prompts/table_description.md`, 4 new
test files. Changed: `app/catalog/sync.py` (UPSERT), `.env.example` +
`requirements.txt` (new deps/vars), `tests/test_catalog_sync.py` (one
test replaced), `tests/test_env_example.py` (extended). Full mechanics in
`plans/logs/_auto-capture.md` and `artifacts/reviews/2026-08-02-llm-table-descriptions.md`.

## The done-check output
```
$ python -m app.catalog.verify_describe
Descriptions:
  [OK] olist.customers: description=763 chars
  [OK] olist.geolocation: description=1107 chars
  [OK] olist.order_items: description=1019 chars
  [OK] olist.order_payments: description=854 chars
  [OK] olist.order_reviews: description=899 chars
  [OK] olist.orders: description=1028 chars
  [OK] olist.product_category_name_translation: description=901 chars
  [OK] olist.products: description=948 chars
  [OK] olist.sellers: description=864 chars

verify_describe: PASSED

$ python -m app.catalog.describe   # second run, right after the first
  olist.customers: already described, skipping
  ... (8 more "skipping" lines)
Table description sync complete.
real  0m1.018s   # zero LLM calls -- DB-only round trip

$ python -m app.catalog.sync && python -m app.catalog.verify_describe
Catalog sync complete.
...
verify_describe: PASSED   # descriptions survived the re-sync

$ python -m unittest discover tests
............................................................
----------------------------------------------------------------------
Ran 60 tests in 36.222s

OK
```

## One thing you rejected or changed
Two things, both from the Gate 2 no-slop pass:
1. Rejected the first cut of `call_llm_for_description`'s retry loop —
   the Anthropic API call sat *outside* the `try`/retry scope, so a live
   network failure on attempt 1 would crash the whole run instead of
   getting the one retry the brief requires. Required moving the API call
   inside the same `try` so network and validation failures share the
   retry.
2. Caught mid-build (not at review): my own new test in
   `tests/test_catalog_sync.py` hand-set `customers.description` to a
   throwaway string to prove the UPSERT preserves it, but didn't restore
   the original value afterward — it leaked into the real DB and made
   `describe.py` permanently skip `customers` (since it was no longer
   NULL). Fixed with a try/finally restoring the original value, and
   manually repaired the polluted row before re-running `describe.py` for
   real.

## The next smallest slice
Add `prompts/generate_sql.md` + a CLI that takes one hardcoded question,
builds a whole-schema context block from `catalog_tables`/`catalog_columns`
(no retrieval yet, per M2), calls the LLM once, and prints the raw
generated SQL — no validation or execution yet, kept as its own slice
after this one so the sqlglot/catalog safety gate gets its own dedicated
review.
