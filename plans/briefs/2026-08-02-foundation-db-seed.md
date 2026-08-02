# Brief — Foundation DB + seed

Date: 2026-08-02
Milestone: M1 Foundation (PLAN.md)

Goal:
From a clean clone, `docker compose up` plus one seed command produce a
Postgres 16 + pgvector instance with the full Olist dataset loaded into
an `olist` schema and a SELECT-only `olist_ro` user.

Constraints:
postgres:16 + pgvector image, one instance (ARCHITECT.md: one Postgres,
multiple schemas — no Qdrant/Redis); seed idempotent, safe to re-run;
`olist_ro` gets zero DDL/DML grants beyond SELECT (ARCHITECT.md: blast-
radius isolation via a dedicated read-only user is the product's core
safety property); seed/verify scripts use plain psycopg/asyncpg, no ORM;
secrets via `.env`, `.env.example` committed and kept current; no app
schema, no FastAPI, no LLM calls in this slice.

Inputs:
PRD.md §5-6 and §12 week 1; the 9 Olist CSV files, manually downloaded
from Kaggle by the user and placed in `data/` (Kaggle auth is a manual,
out-of-band step — documented, not scripted); Docker Desktop.

Outputs:
- `docker-compose.yml` — db service only (postgres:16 + pgvector image,
  volume, env-driven credentials).
- `scripts/seed.py` — creates `olist` schema, loads all 9 CSVs, creates
  `olist_ro` with SELECT-only grants; idempotent (safe to re-run without
  duplicating rows or failing on already-applied grants).
- `scripts/verify_seed.py` — the done-check script.
- `.env.example` — all required env vars with placeholder values.
- `data/README.md` — exact Kaggle dataset URL, expected filenames, where
  to place them.

Done-check:
`python scripts/verify_seed.py` — exits 0 only if: all 9 `olist` tables
exist with row counts matching the corresponding `data/*.csv` line counts
(no hardcoded row numbers — counts are read from the CSVs at verify
time, so the check holds regardless of exact dataset revision); the
`vector` extension is installed; an `INSERT` attempted as `olist_ro`
raises a permissions error.

Out-of-scope:
Catalog sync and table descriptions, embeddings/glossary, any LLM call,
the `app` schema and its tables, FastAPI, frontend, CI, scripted Kaggle
API download.
