# Brief — Catalog sync CLI

Date: 2026-08-02
Milestone: M1 Foundation (catalog sync CLI)

Goal:
A CLI command, `python -m app.catalog.sync`, introspects every table and
column in the `olist` schema and persists it into two new `app` schema
tables, `catalog_tables` and `catalog_columns`, matching PRD.md §7's exact
column shapes.

Constraints:
Plain psycopg2, no ORM/SQLAlchemy (FastAPI/SQLAlchemy hasn't landed yet;
stay consistent with the M1 seed slice's stack). Connects as the
`POSTGRES_USER` owner role (needs to create the `app` schema and
introspect `olist`) — never the `olist_ro` read-only role. Sync must be
idempotent (safe to re-run — truncate + reinsert both catalog tables per
run). No LLM calls this slice — `catalog_tables.description` stays NULL
(PRD F4's one-paragraph LLM description is a separate, later slice: a
genuinely different concern — prompts/*.md, Pydantic validation, retry).
No embeddings — `kb_chunks`/pgvector writes are M3 scope. No change to
the `olist` schema tables themselves.

`catalog_tables.ddl_summary` is a reconstructed CREATE-TABLE-style text
per table (column name, type, NULL/NOT NULL) — the only place nullability
is recorded, since `catalog_columns` per PRD §7 has no nullable column of
its own. `sample_values_json` per column is the up-to-5 **distinct**
non-null values, `ORDER BY <col> ASC LIMIT 5` — deterministic and
reproducible run to run, so the done-check can assert exact values.

Inputs:
PRD.md §4 (F4 — Schema catalog) and §7 (Data Model, app schema — exact
`catalog_tables`/`catalog_columns` column shapes); ARCHITECT.md (one
Postgres instance, multiple schemas); the seeded `olist` schema and
`olist_ro` user from the prior slice; Postgres
`information_schema`/`pg_catalog` for introspection (columns, primary
keys via `information_schema.table_constraints`/`key_column_usage`,
foreign keys similarly).

Outputs:
- `app/__init__.py`, `app/catalog/__init__.py` — first code under the
  `app/` package (the future FastAPI backend lives here from M4 on; this
  slice only adds the catalog submodule).
- `app/catalog/sync.py` — the CLI (`python -m app.catalog.sync`): creates
  `app` schema + `catalog_tables(id, table_name, description, row_count,
  ddl_summary)` and `catalog_columns(id, table_id, column_name,
  data_type, is_pk, is_fk, ref_table, sample_values_json)` if absent,
  introspects all 9 `olist` tables, truncates and reinserts both catalog
  tables each run.
- `app/catalog/verify_sync.py` — the done-check script.

Done-check:
`python -m app.catalog.verify_sync` — exits 0 only if: `app.catalog_tables`
has exactly 9 rows (one per `olist` table) with `row_count` matching the
live `olist.*` counts and a non-empty `ddl_summary` per table;
`app.catalog_columns` has exactly one row per real column of every
`olist` table (matching `information_schema.columns`); every column with
a real primary-key constraint has `is_pk = true` (no false positives or
negatives); every column with a real foreign-key constraint has
`is_fk = true` and the correct `ref_table`; every column's
`sample_values_json` holds up to 5 distinct, ascending-ordered non-null
values (fewer only when the table has fewer distinct values).

Out-of-scope:
LLM-generated table descriptions (`catalog_tables.description` stays
NULL), embeddings/pgvector writes to `kb_chunks`, the business glossary
(F5), any change to `olist` schema tables, FastAPI, frontend, CI,
`prompts/*.md`.
