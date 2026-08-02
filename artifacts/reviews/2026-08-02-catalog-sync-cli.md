# Review gate — Catalog sync CLI

Date: 2026-08-02
Brief: plans/briefs/2026-08-02-catalog-sync-cli.md
Diff reviewed: staged working-tree diff (app/, tests/, plans/briefs/) — 8 new files, 987 insertions, no existing files modified.

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review
8 new files, all net-new (no existing code touched): `app/__init__.py`,
`app/catalog/__init__.py`, `app/catalog/sync.py` (221 lines),
`app/catalog/verify_sync.py` (178 lines), `tests/_catalog_helpers.py`,
`tests/test_catalog_sync.py`, `tests/test_verify_sync_script.py`,
`plans/briefs/2026-08-02-catalog-sync-cli.md`. Every line was read.
PASS.

## 2. The stated goal matches the actual change
Brief goal: `python -m app.catalog.sync` introspects `olist` and persists
it into `app.catalog_tables`/`app.catalog_columns` matching PRD §7. The
diff does exactly that — introspection is entirely `information_schema`-
driven (no hardcoded table list), `ddl_summary` is a reconstructed
CREATE-TABLE text carrying nullability, sample values are 5 distinct
ascending non-null values, sync is truncate+reinsert idempotent, and it
connects only as `POSTGRES_USER`. No extra behavior smuggled in —
`catalog_tables.description` stays NULL, no embeddings, no LLM calls, no
`olist` schema changes. PASS.

## 3. The eval or test passed
```
$ python -m app.catalog.sync
  olist.customers: 5 columns, 99441 rows
  olist.geolocation: 5 columns, 1000163 rows
  olist.order_items: 7 columns, 112650 rows
  olist.order_payments: 5 columns, 103886 rows
  olist.order_reviews: 7 columns, 99224 rows
  olist.orders: 8 columns, 99441 rows
  olist.product_category_name_translation: 2 columns, 71 rows
  olist.products: 9 columns, 32951 rows
  olist.sellers: 4 columns, 3095 rows
Catalog sync complete.

$ python -m app.catalog.verify_sync
Table rows:
  [OK] app.catalog_tables: 9 rows (expected 9)
  [OK] olist.customers ... (all 9 OK)
Columns:
  [OK] ... (all 9 OK)
Primary keys:
  [OK] primary keys match live introspection
Foreign keys:
  [OK] foreign keys match live introspection
Sample values:
  [OK] sample values match live introspection

verify_sync: PASSED
EXIT:0

$ python -m unittest discover tests -v
... (42 tests, including 13 new catalog tests)
Ran 42 tests in 24.488s

OK
```
PASS.

## 4. The no-slop review found no unresolved issues
First no-slop-reviewer pass found 4 issues:
1. Duplication of `require_env`/`connect` from `scripts/seed.py` with no
   written justification — fixed by adding an in-code comment explaining
   why (different trees, different futures — `app/`'s eventual FastAPI
   code uses asyncpg per ARCHITECT.md; only the 2nd occurrence).
2. `connect()` carried unused `user_env`/`password_env` parameterization
   copied from `seed.py` — fixed by removing it; `sync.py`'s `connect()`
   now always uses `POSTGRES_USER`/`POSTGRES_PASSWORD`, no arguments.
3. `test_olist_ro_lacks_create_privilege_on_app_schema` only checked
   `has_schema_privilege()`, not real behavior — fixed by adding
   `test_sync_run_as_olist_ro_actually_fails`, which runs the actual CLI
   via subprocess with RO credentials and asserts it fails with
   `InsufficientPrivilege`.
4. `import json` nested inside a function in `verify_sync.py` instead of
   at module top-level — fixed.

A second no-slop-reviewer pass confirmed all 4 fixes landed correctly
with no regressions, and found one low-severity residual: the done-
check's "fewer only when the table has fewer distinct values" branch is
never exercised by any test, because every real `olist` column happens
to have ≥5 distinct non-null values with the current dataset — not a
bug, an untestable edge with this data. Accepted as a documented
exception rather than fabricating synthetic data to force coverage.
PASS.

## 5. The shipping proof is attached
Ran `python -m app.catalog.sync` for real against the live seeded
Postgres instance (docker compose `db` service) — see check 3 output
above — then `python -m app.catalog.verify_sync` confirms the result
end-to-end against live `information_schema` introspection, not just
against the test suite's mocks (there are none — all tests hit the real
DB).

## Rejected or changed
The weak `has_schema_privilege`-only RO-role test was rejected in favor
of a real behavioral probe; the dead `user_env`/`password_env`
parameters on `sync.py`'s `connect()` were removed.

## Verdict
accept — all five checks green.
