# Slice log — Catalog sync CLI

Date: 2026-08-02
Brief: plans/briefs/2026-08-02-catalog-sync-cli.md

## The plan you approved
Mirror `scripts/seed.py`/`verify_seed.py`'s connection/transaction/output
conventions under a new `app/catalog` package: introspect the `olist`
schema entirely via `information_schema` (no hardcoded table list),
build a reconstructed CREATE-TABLE-style `ddl_summary` per table (the
only place nullability is recorded), and 5 distinct ascending non-null
sample values per column. Truncate + reinsert each run; connect only as
`POSTGRES_USER`.

## The diff you accepted
Commit b55ae95 — "Catalog sync CLI: introspect olist schema into
app.catalog_tables/columns". 9 files, 1093 insertions. Full mechanics in
plans/logs/_auto-capture.md; full check-by-check record in
artifacts/reviews/2026-08-02-catalog-sync-cli.md.

## The done-check output
```
$ python -m app.catalog.verify_sync
Table rows:
  [OK] app.catalog_tables: 9 rows (expected 9)
  [OK] olist.customers: row_count=99441 (expected 99441), ddl_summary=set
  [OK] olist.geolocation: row_count=1000163 (expected 1000163), ddl_summary=set
  [OK] olist.order_items: row_count=112650 (expected 112650), ddl_summary=set
  [OK] olist.order_payments: row_count=103886 (expected 103886), ddl_summary=set
  [OK] olist.order_reviews: row_count=99224 (expected 99224), ddl_summary=set
  [OK] olist.orders: row_count=99441 (expected 99441), ddl_summary=set
  [OK] olist.product_category_name_translation: row_count=71 (expected 71), ddl_summary=set
  [OK] olist.products: row_count=32951 (expected 32951), ddl_summary=set
  [OK] olist.sellers: row_count=3095 (expected 3095), ddl_summary=set
Columns:
  [OK] olist.customers: 5 columns
  [OK] olist.geolocation: 5 columns
  [OK] olist.order_items: 7 columns
  [OK] olist.order_payments: 5 columns
  [OK] olist.order_reviews: 7 columns
  [OK] olist.orders: 8 columns
  [OK] olist.product_category_name_translation: 2 columns
  [OK] olist.products: 9 columns
  [OK] olist.sellers: 4 columns
Primary keys:
  [OK] primary keys match live introspection
Foreign keys:
  [OK] foreign keys match live introspection
Sample values:
  [OK] sample values match live introspection

verify_sync: PASSED
```
Plus `python -m unittest discover tests`: 42 tests, OK (28 prior + 14 new).

## One thing you rejected or changed
Two rounds of no-slop review found and fixed 4 issues before merge: the
`require_env`/`connect` duplication from `scripts/seed.py` had no written
justification (fixed with an in-code comment); `connect()` carried dead
`user_env`/`password_env` parameterization copied from `seed.py` that
nothing in this module ever used (removed — it always connects as
`POSTGRES_USER` now, never parameterized); `test_olist_ro_lacks_create_
privilege_on_app_schema` only checked `has_schema_privilege()` instead of
proving the restriction behaviorally (rejected, replaced with
`test_sync_run_as_olist_ro_actually_fails`, which runs the real CLI under
RO credentials and asserts it fails with `InsufficientPrivilege`); a
nested `import json` was moved to module top-level.

This is the second time no-slop caught a test that checked a state/config
proxy instead of triggering the real behavior (foundation-db-seed's env-
var KeyError fix originally had no test forcing the missing-var path).
Promoted to templates/no-slop.md's "Untested edges" category so
test-writer/no-slop passes catch this class of gap without a review
round-trip next time.

One accepted, undismissed finding: the done-check's "fewer than 5
distinct values" branch is never exercised by any test, because every
real `olist` column happens to have ≥5 distinct non-null values with the
current dataset. Left as a documented exception rather than fabricating
synthetic data to force coverage of an edge the real data doesn't have.

## The next smallest slice
LLM-generated table descriptions: one paragraph per `catalog_tables` row,
generated via a single LLM call per table (versioned prompt in
prompts/*.md, Pydantic-validated with one retry per ARCHITECT.md),
run once and cached into the `description` column this slice
deliberately left NULL — finishes M1 exactly as PLAN.md scopes it.
