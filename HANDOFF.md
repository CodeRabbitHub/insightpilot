# Handoff

Date: 2026-08-04
Slice just completed: plans/briefs/2026-08-04-fastapi-ask-stream-endpoint.md +
  plans/logs/2026-08-04-fastapi-ask-stream-endpoint.md (commit 96a4397)

## State of the work
- **`POST /api/ask/stream` exists and works: `get_answer(question)`'s
  outcome is now deliverable as Server-Sent Events, proving
  ARCHITECT.md's "SSE, not WebSockets" transport decision end-to-end.**
  `app/main.py` gained a second route, additive to the existing
  `POST /api/ask` (untouched, still 502-on-failure). The new route
  hand-rolls SSE via Starlette's `StreamingResponse` (no new
  dependency) over an async generator that runs `get_answer()` once and
  yields exactly one event: `event: result\ndata: {"sql", "rows"}\n\n`
  on success, or `event: error\ndata: {"detail"}\n\n` on any failure.
  Unlike `/api/ask`, the HTTP status is always 200 — once the stream
  has started there is no later status code to change, so the outcome
  is signaled by the event type instead.
- The success payload is built via `AskResponse(sql=sql, rows=rows)` —
  the same Pydantic model `/api/ask` already validates through — not a
  hand-built dict, so both endpoints validate `get_answer()`'s output
  identically (a no-slop pre-gate finding, fixed before merge).
- `tests/test_api_ask_stream.py` (11 tests, real, no mocking of the
  LLM/DB except one deliberate seam mirroring `test_api_ask.py`'s
  precedent): a happy-path class making one real, billed pipeline call
  through `TestClient(...).stream(...)`, asserting exactly one `result`
  event with non-empty `sql`/`rows` and no `error` event; a
  failure-path class patching `app.main.get_answer`, asserting exactly
  one `error` event with a non-empty `detail` and no `result` event,
  and — critically — HTTP 200 in both cases, not a crash or hang.
- `CLAUDE.md`'s Commands section documents the new route alongside the
  existing `/api/ask` line.
- No `app/pipeline/*` file was touched. Full suite: 208/208 passing
  (197 prior + this slice's 11).

## Proof
```
$ .venv/Scripts/python.exe -m unittest discover -s tests -p "test_api_ask_stream.py" -v
test_body_contains_exactly_one_error_event ... ok
test_body_contains_no_result_event ... ok
test_error_event_data_has_a_non_empty_detail_string ... ok
test_pipeline_exception_is_not_a_crash_or_hung_stream ... ok
test_pipeline_exception_still_returns_200_not_an_http_error ... ok
test_body_contains_exactly_one_result_event ... ok
test_body_contains_no_error_event ... ok
test_result_event_data_has_exactly_the_sql_and_rows_keys ... ok
test_result_event_rows_is_a_non_empty_list ... ok
test_result_event_sql_is_a_non_empty_string ... ok
test_returns_200_for_the_fixed_question ... ok

Ran 11 tests in 8.162s

OK
```
```
$ .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
$ curl -N -X POST localhost:8000/api/ask/stream -H "Content-Type: application/json" \
    -d '{"question": "What are the top 5 product categories by number of orders?"}' \
    -w "\nHTTP_STATUS:%{http_code}\n"
event: result
data: {"sql": "SELECT p.product_category_name, COUNT(DISTINCT oi.order_id) AS order_count FROM olist.order_items oi JOIN olist.products p ON oi.product_id = p.product_id GROUP BY p.product_category_name ORDER BY order_count DESC LIMIT 5", "rows": [{"product_category_name": "cama_mesa_banho", "order_count": 9417}, {"product_category_name": "beleza_saude", "order_count": 8836}, {"product_category_name": "esporte_lazer", "order_count": 7720}, {"product_category_name": "informatica_acessorios", "order_count": 6689}, {"product_category_name": "moveis_decoracao", "order_count": 6449}]}
HTTP_STATUS:200
```
Also confirmed live: an empty question produces `event: error` with a
real non-empty `detail`, still HTTP 200. Full detail:
`artifacts/reviews/2026-08-04-fastapi-ask-stream-endpoint.md`.

## Open questions / known issues
- **Decimal-valued rows still serialize as JSON strings, not numbers**
  (carried over, unchanged this slice) — both `/api/ask` and
  `/api/ask/stream` now share this via the same `AskResponse` +
  `jsonable_encoder` path. Not a bug, but the eventual chart-rendering
  work needs to parse numeric-looking strings, not assume native JSON
  numbers.
- **`plans/logs/_auto-capture.md` remains silently uncommitted across
  every commit** (pre-existing workflow gap, still not decided —
  commit it every time? gitignore it? — flagging again since it's now
  4+ commits deep, not fixed, not a regression from this slice).
- Starlette's `TestClient` still emits the `httpx2` deprecation
  warning — harmless, not acted on (new dependency without asking).
- `tests/test_seed_idempotency.py`'s own real Postgres deadlock (M1-era,
  unrelated code) remains uninvestigated.
- The doubled-Voyage-call-per-question design cost
  (`app/pipeline/generate_sql.py`) remains unoptimized — accepted,
  documented in code.
- Lint/type tooling (`ruff`, `mypy`) and the test runner (`unittest`,
  not `pytest`) remain unaddressed, carried over from every prior slice.
- The concurrency-safety pattern (session-scoped advisory locks) is
  still scoped to exactly the two test classes it was applied to.
- **The `app` schema does not exist in Postgres yet** — confirmed by
  grep: only `scripts/seed.py` creates `olist` (`CREATE SCHEMA IF NOT
  EXISTS olist`). The next slice's migration must create `app` itself,
  not just tables inside it.

## Next slice (the brief, written NOW while context is hot)
Goal:
Add the `app` schema's persistence foundation — a SQLAlchemy async
read-write pool (distinct from `execute_sql()`'s read-only asyncpg
pool), one Alembic migration creating the `app` schema plus
`conversations` and `messages` tables, and their ORM models — proven by
a real round-trip (write then read back) against the dev Postgres
instance. This is the foundation only: wiring `/api/ask`/
`/api/ask/stream` to actually persist a conversation+message per
request is deliberately a separate, following slice.

Constraints:
- SQLAlchemy 2.0 (async) + Alembic — both already named in PRD.md's
  Backend stack table and ARCHITECT.md's two-pool decision, so adding
  them isn't a fresh "new dependency" ask, but still pin exact current
  versions in `requirements.txt` (mirroring the fastapi/uvicorn slice's
  precedent) and confirm at Gate 1.
- Reuse the existing `asyncpg` driver via SQLAlchemy's
  `postgresql+asyncpg://` async dialect — no additional DB driver
  dependency.
- The new pool authenticates as `POSTGRES_USER`
  (`insightpilot_owner`, already in `.env`/`.env.example`) — read-write,
  scoped to the `app` schema only. It must never touch `olist` schema
  tables and generated SQL must never run through it — that stays
  exclusively `execute_sql()`'s read-only `OLIST_RO_USER` asyncpg pool.
  This is ARCHITECT.md's blast-radius-isolation design; the two pools
  must stay architecturally separate, not merged for convenience.
- The migration must create the `app` schema itself
  (`CREATE SCHEMA IF NOT EXISTS app`) before creating tables inside it
  — it doesn't exist yet in any environment.
- Scope to exactly two tables from PRD.md §7's data model:
  `conversations` (id, title, created_at) and `messages` (id,
  conversation_id FK, role, content_json, created_at). Do NOT add
  `users`, `queries`, or `dashboards` — `users`/auth needs F8 (not
  built yet); `queries`/`dashboards` are separate later slices.
- PRD.md's `conversations` table has a `user_id` FK to `users`, but
  `users` doesn't exist yet — omit that column/FK for this slice
  (document it as a gap to close when F8 lands), rather than blocking
  this slice on building auth early or out of order.
- No changes to `app/main.py`'s existing `/api/ask`/`/api/ask/stream`
  routes or their contracts, and no wiring of this new persistence
  layer into either endpoint — this slice is schema/pool/models only,
  proven by a direct test against the pool, not through HTTP.
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
- `requirements.txt` — current dependency list.

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
  this one, once the foundation exists).
- Any change to `app/pipeline/*` or the existing `/api/ask*` endpoints'
  contracts.
- Lint/type tooling, `_auto-capture.md`'s uncommitted-backlog question,
  `test_seed_idempotency.py`'s deadlock (all carried over, untouched).
