# Review gate — Foundation DB + seed

Date: 2026-08-02
Brief: plans/briefs/2026-08-02-foundation-db-seed.md
Diff reviewed: staged diff vs HEAD (95a20c2, the Phase 0 scaffold commit) — 18 files, 1102 insertions, 0 deletions

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review
18 files, all additive (no deletions). `.env.example`, `.gitignore`,
`data/README.md`, `docker-compose.yml`, `requirements.txt`,
`scripts/seed.py`, `scripts/verify_seed.py`, 9 test files, the brief
itself, and the auto-capture log. Read in full. PASS.

## 2. The stated goal matches the actual change
Brief's Goal: "From a clean clone, `docker compose up` plus one seed
command produce a Postgres 16 + pgvector instance with the full Olist
dataset loaded into an `olist` schema and a SELECT-only `olist_ro` user."
The diff delivers exactly this: a single-service compose file, an
idempotent seed script (typed tables, CSV load, RO role + grants), a
verify script matching the done-check verbatim, `.env.example`, and
`data/README.md`. No extra scope (no catalog sync, embeddings, FastAPI,
`app` schema, CI) and nothing missing. PASS.

## 3. The eval or test passed
Done-check, run fresh:
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
Full test suite: `Ran 28 tests in 21.442s` / `OK`.

## 4. The no-slop review found no unresolved issues
Two no-slop-reviewer passes. First pass (pre-gate) found 3 issues, all
fixed:
- `verify_seed.py` hardcoded `"olist.customers"` in the permission probe
  → now derives `probe_table = TABLES[0][1]` from the single source of
  truth in `seed.py`.
- Bare `os.environ[...]` gave raw `KeyError` on missing config → added
  `require_env()` in `seed.py`, raising a `SystemExit` with a clear
  "copy .env.example to .env" message; reused in both scripts.
- `requirements.txt` was unpinned → pinned to
  `psycopg2-binary==2.9.12`, `python-dotenv==1.2.2` (exact versions
  verified installed and working this session).

Second pass (final) found 1 low-severity gap: the `require_env()` fix
itself had no regression test. Fixed by adding
`tests/test_require_env.py`. Final pass: clean, no open findings across
all 10 rubric categories.

One reviewer suggestion was heard and explicitly not actioned (see
Rejected or changed below).

## 5. The shipping proof is attached
Full clean-slate run, not just automated tests:
```
docker compose down -v   # removed container + volume entirely
docker compose up -d     # fresh container, healthy after 4 tries
pip install -r requirements.txt
python scripts/seed.py       # loaded all 9 tables from scratch
python scripts/verify_seed.py -> verify_seed: PASSED (exit 0)
```
Plus live proof beyond the scripted checks, via `psql` directly against
the running container:
- A real cross-table aggregate (`JOIN olist.orders`/`order_items`,
  `GROUP BY` month, `SUM(price)`) returned correct monthly order
  counts/revenue — proves the typed `NUMERIC`/`TIMESTAMP` columns work
  for actual analytics queries, not just row counts.
- `olist_ro` successfully ran `SELECT COUNT(*) FROM olist.orders` (99441).
- `olist_ro` was denied `DELETE FROM olist.orders ...` with
  `ERROR: permission denied for table orders`.

## Rejected or changed
The no-slop reviewer's suggestion to add negative-path tests (missing
CSV, malformed row, DB unreachable during seed) was heard and not
actioned — out of scope for a foundation slice whose brief's own
done-check is happy-path only; revisit only if a later slice's seed
process needs to be more defensive.

## Verdict
**accept** — all five checks green.
