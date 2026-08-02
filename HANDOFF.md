# Handoff

Date: 2026-08-02
Slice just completed: plans/briefs/2026-08-02-foundation-db-seed.md +
  plans/logs/2026-08-02-foundation-db-seed.md (commit 4e1745b)

## State of the work
- Repo git-initialized (main branch); Phase 0 scaffold committed
  (95a20c2), Foundation DB + seed slice committed (4e1745b).
- `docker-compose.yml` brings up a single `db` service
  (`pgvector/pgvector:pg16`), env-driven credentials, persistent volume,
  healthcheck.
- `scripts/seed.py` idempotently loads the 9 Olist CSVs (already present
  in `data/`, gitignored) into typed tables under an `olist` schema, and
  provisions a SELECT-only `olist_ro` role (verified via live `psql`:
  can SELECT, denied INSERT/UPDATE/DELETE/CREATE).
- `scripts/verify_seed.py` is the working done-check: row counts
  (CSV-parsed via `csv.reader`, not raw line count — `order_reviews` has
  embedded newlines in `review_comment_message`), `vector` extension
  installed, `olist_ro` permission enforcement.
- 28 tests pass (`python -m unittest discover tests`), covering schema,
  RO permissions (behavioral + grant-level), seed idempotency, the
  verify script itself, docker-compose structure, `.env.example`, and
  `data/README.md`.
- `requirements.txt` (new): `psycopg2-binary==2.9.12`,
  `python-dotenv==1.2.2` — first Python deps in the repo.
- Local `.env` created (gitignored) from `.env.example`; local Postgres
  runs on host port 5433 (5432 was occupied by an unrelated container on
  this machine) — `.env.example` itself still documents the sane default
  of 5432.
- Gate 2 accepted: artifacts/reviews/2026-08-02-foundation-db-seed.md.

## Proof
```
$ python scripts/verify_seed.py
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
Full suite: `Ran 28 tests ... OK`.

## Open questions / known issues
- Test runner: kit hook runs `unittest`; project will likely move to
  pytest once FastAPI test deps land in M4 — that slice must update
  `.claude/hooks/stop_verify.py` TEST_CMD and CLAUDE.md together (carried
  over from Phase 0, still unresolved).
- No FK constraints were added between `olist.*` tables (e.g.
  `order_items.order_id` → `orders.order_id`) — deliberately kept simple
  since the brief's done-check didn't require referential integrity and
  it would complicate drop/recreate ordering. Revisit if the SQL pipeline
  (M2+) needs the planner to see explicit FK relationships.
- Host Postgres port is machine-specific (5433 here, another container
  already held 5432) — a fresh clone on a different machine may need no
  change at all (5432 will likely be free), `.env.example` still defaults
  to 5432 correctly.

## Next slice (the brief, written NOW while context is hot)
Goal:
A CLI command, `python -m app.catalog.sync`, introspects every table and
column in the `olist` schema — data type, nullability, primary/foreign
keys, live row count, and up to 5 sample values per column — and
persists it into two new `app` schema tables, `catalog_tables` and
`catalog_columns`, matching PRD.md §7's exact column shapes.

Constraints:
No LLM calls this slice — `catalog_tables.description` stays NULL;
generating the one-paragraph LLM description per table (PRD.md F4: "run
once, cached") is a separate, later slice, since it's a genuinely
different outcome (introspection vs. LLM generation) with its own
concerns (prompts/*.md, Pydantic validation, retry). No embeddings —
`kb_chunks` / pgvector writes are M3 scope (PLAN.md), not this slice.
Plain psycopg2, no ORM/SQLAlchemy (FastAPI/SQLAlchemy hasn't landed yet;
stay consistent with the M1 seed slice's stack). Sync must be idempotent
(safe to re-run — truncate + reinsert both catalog tables per run).
Connects as the `POSTGRES_USER` owner role (needs to create the `app`
schema and introspect `olist`) — never the `olist_ro` read-only role.
No change to the `olist` schema tables themselves.

Inputs:
PRD.md §4 (F4 — Schema catalog) and §7 (Data Model, app schema — exact
`catalog_tables`/`catalog_columns` column shapes); ARCHITECT.md (one
Postgres instance, multiple schemas); the seeded `olist` schema and
`olist_ro` user from the just-completed slice; Postgres
`information_schema`/`pg_catalog` for introspection (columns, primary
keys via `information_schema.table_constraints`/`key_column_usage`,
foreign keys similarly).

Outputs:
- `app/__init__.py`, `app/catalog/__init__.py` — first code under the
  `app/` package (the future FastAPI backend lives here from M4 on; this
  slice only adds the catalog submodule).
- `app/catalog/sync.py` — the CLI (`python -m app.catalog.sync`):
  creates `app` schema + `catalog_tables`/`catalog_columns` tables if
  absent, introspects all 9 `olist` tables, truncates and reinserts both
  catalog tables each run.
- `app/catalog/verify_sync.py` — the done-check script.

Done-check:
`python -m app.catalog.verify_sync` — exits 0 only if: `app.catalog_tables`
has exactly 9 rows (one per `olist` table) with `row_count` matching the
live `olist.*` counts; `app.catalog_columns` has exactly one row per real
column of every `olist` table (matching `information_schema.columns`);
every column with a real primary-key constraint has `is_pk = true` (no
false positives or negatives); every column with a real foreign-key
constraint has `is_fk = true` and the correct `ref_table`; every column's
`sample_values_json` is populated with up to 5 values (fewer only when
the table has fewer distinct values).

Out-of-scope:
LLM-generated table descriptions (`catalog_tables.description` stays
NULL), embeddings/pgvector writes to `kb_chunks`, the business glossary
(F5), any change to `olist` schema tables, FastAPI, frontend, CI,
`prompts/*.md`.
