# Slice log — Foundation DB + seed

Date: 2026-08-02
Brief: plans/briefs/2026-08-02-foundation-db-seed.md

## The plan you approved
Single-service docker-compose (pgvector/pgvector:pg16), an idempotent
seed.py loading 9 typed Olist tables via COPY plus an olist_ro SELECT-only
role (default privileges so re-seeding doesn't lose grants), and a
verify_seed.py done-check comparing table row counts to CSV-parsed (not
raw line) counts.

## The diff you accepted
Commit 4e1745b — "Foundation DB + seed: Postgres 16 + pgvector, Olist
data, RO user". 19 files, 1197 insertions. Full mechanics in
plans/logs/_auto-capture.md; full check-by-check record in
artifacts/reviews/2026-08-02-foundation-db-seed.md.

## The done-check output
```
Row counts:
  [OK] olist.customers: 99441 rows (expected 99441)
  [OK] olist.geolocation: 1000163 rows (expected 1000163)
  [OK] olist.order_items: 112650 rows (expected 112650)
  [OK] olist.order_payments: 103886 rows (expected 103886)
  [OK] olist.order_reviews: 99224 rows (expected 99224)
  [OK] olist.orders: 99441 rows (expected 99441)
  [OK] olist.products: 32951 rows (expected 32951)
  [OK] olist.sellers: 3095 rows (expected 3095)
  [OK] olist.product_category_name_translation: 71 rows (expected 71)
Extensions:
  [OK] vector extension installed
Permissions:
  [OK] olist_ro denied INSERT (permissions enforced)

verify_seed: PASSED
```
Plus `python -m unittest discover tests`: 28 tests, OK.

## One thing you rejected or changed
Two rounds of no-slop review found and fixed 4 issues before merge:
hardcoded probe table name in verify_seed.py, bare `os.environ[...]`
giving raw KeyErrors instead of an actionable message, unpinned deps in
requirements.txt, and the fix for the KeyError issue itself having no
regression test (added tests/test_require_env.py). Separately, the
reviewer's suggestion to add negative-path tests (missing/malformed CSV,
DB unreachable) was heard and explicitly declined — out of scope for a
foundation slice whose own done-check is happy-path only.

A real bug surfaced independently during manual verification, not by the
reviewer: `order_reviews` loaded 99,224 rows against a naive `wc -l`-style
expectation of 104,719 — `review_comment_message` contains embedded
newlines inside quoted CSV fields, so raw line-counting overcounts rows.
Fixed by making verify_seed.py's row-count check csv.reader-based instead
of a raw line count (matching what the test-writer's tests/_pg_helpers.py
already did correctly). Worth remembering for any future CSV-adjacent
work in this project: never trust `wc -l` / naive line splitting against
Olist's free-text columns.

## The next smallest slice
Catalog sync CLI: introspect all `olist.*` tables/columns (types, PKs/FKs,
row counts, sample values) into a queryable catalog with LLM-generated
table/column descriptions cached — finishes M1 as scoped in PLAN.md and
is the schema-context dependency both M2 (SQL generation) and M3
(retrieval) need next.
