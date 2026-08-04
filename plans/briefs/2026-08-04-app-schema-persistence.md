# Brief — `app` schema persistence foundation

Date: 2026-08-04
Milestone: M4 API (third slice — persistence foundation only; wiring the
  HTTP/SSE endpoints to actually persist is the following slice)

Goal:
Stand up the `app` schema's persistence foundation — a SQLAlchemy async
read-write pool distinct from `execute_sql()`'s read-only asyncpg pool,
one Alembic migration creating the `app` schema plus `conversations` and
`messages` tables, and their ORM models — proven by a real round-trip
(write then read back) against the dev Postgres instance.

Constraints:
- SQLAlchemy 2.0 (async) + Alembic — both already named in PRD.md's
  Backend stack table and ARCHITECT.md's two-pool decision, so this
  isn't a fresh "new dependency" ask, but pin exact current versions in
  `requirements.txt` (mirroring the fastapi/uvicorn slice's precedent)
  and confirm at Gate 1.
- Reuse the existing `asyncpg` driver via SQLAlchemy's
  `postgresql+asyncpg://` async dialect — no additional DB driver
  dependency.
- The new pool authenticates as `POSTGRES_USER` (`insightpilot_owner`,
  already in `.env`/`.env.example`) — read-write, scoped to the `app`
  schema only. It must never touch `olist` schema tables, and generated
  SQL must never run through it — that stays exclusively
  `execute_sql()`'s read-only `OLIST_RO_USER` asyncpg pool. This is
  ARCHITECT.md's blast-radius-isolation design; the two pools stay
  architecturally separate, not merged for convenience.
- The migration must create the `app` schema itself (`CREATE SCHEMA IF
  NOT EXISTS app`) before creating tables inside it — it doesn't exist
  yet in any environment (confirmed by grep: only `scripts/seed.py`
  creates `olist`).
- Scope to exactly two tables from PRD.md §7's data model:
  `conversations` (id, title, created_at) and `messages` (id,
  conversation_id FK, role, content_json, created_at). Do NOT add
  `users`, `queries`, or `dashboards`.
- PRD.md's `conversations` table has a `user_id` FK to `users`, but
  `users` doesn't exist yet (needs F8) — omit that column/FK this
  slice; document it as a gap to close when F8 lands.
- No changes to `app/main.py`'s existing `/api/ask`/`/api/ask/stream`
  routes or their contracts, and no wiring of this persistence layer
  into either endpoint — schema/pool/models only, proven by a direct
  test against the pool, not through HTTP.
- Tests make a real round-trip against the real dev Postgres instance
  (no mocking the DB) — matches this project's established convention.

Inputs:
- ARCHITECT.md — the two-pool, blast-radius-isolation decision.
- PRD.md §7 — the `app` schema's full data model (reference; this
  slice implements only `conversations` + `messages`).
- `.env.example` — `POSTGRES_USER=insightpilot_owner` already
  provisioned as the schema owner.
- `scripts/seed.py` — existing pattern for schema/role creation
  (`CREATE SCHEMA IF NOT EXISTS olist`) to mirror for `app`.
- `app/pipeline/execute_sql.py` — the existing read-only asyncpg pool,
  as the contrast case for "what this new pool must NOT do."
- `requirements.txt` — current dependency list (fastapi==0.141.1,
  uvicorn[standard]==0.52.1, asyncpg==0.31.0, pydantic==2.13.4, etc.).

Outputs:
- `requirements.txt` gains pinned `sqlalchemy` (2.x, with its async
  extra) and `alembic`.
- New `alembic.ini` + a migrations directory with one migration:
  create the `app` schema, `conversations` table, `messages` table.
- New `app/db/session.py` (or equivalent) — the SQLAlchemy async engine
  + session factory, authenticated as `POSTGRES_USER`.
- New `app/db/models.py` — `Conversation` and `Message` SQLAlchemy 2.0
  declarative ORM models matching the migration.
- `CLAUDE.md`'s Commands section gains the migration-run command
  (e.g. `alembic upgrade head`).
- `tests/test_app_db.py`: a real round-trip test — run the migration
  (or equivalent table creation) against the real dev DB, insert a
  conversation and a message through the ORM, read them back, assert
  the values match. No mocking of the DB.

Done-check:
Both, pasted, fresh, in one sitting:
1. `alembic upgrade head` (or the project's equivalent migration-run
   command) exits 0 against the real dev Postgres instance.
2. `python -m unittest discover -s tests -p "test_app_db.py" -v`
   passing.

Out-of-scope:
- `users` table and any auth (F8 — separate milestone).
- `queries`, `dashboards`, `cards` tables (later F7/F6 slices).
- Wiring `/api/ask` or `/api/ask/stream` to actually create or persist
  a conversation/message per request (the natural next slice after
  this one).
- Any change to `app/pipeline/*` or the existing `/api/ask*` endpoints'
  contracts.
- Lint/type tooling, `_auto-capture.md`'s uncommitted-backlog question,
  `test_seed_idempotency.py`'s deadlock (all carried over, untouched).
