# Handoff

Date: 2026-08-04
Slice just completed: plans/briefs/2026-08-04-app-schema-persistence.md +
  plans/logs/2026-08-04-app-schema-persistence.md (commits a120c4e,
  4d922ee)

## State of the work
- **The `app` schema now has a real persistence foundation: a second
  SQLAlchemy async pool, separate from `execute_sql()`'s read-only
  asyncpg pool, plus `conversations`/`messages` tables and ORM models —
  proven by a real write-then-read-back round trip against the dev
  Postgres instance.** New `app/db/session.py` (`engine` +
  `async_session_factory`, `create_async_engine("postgresql+asyncpg://
  ...")` built via `sqlalchemy.URL.create()`, authenticated as
  `POSTGRES_USER`/`insightpilot_owner`) and `app/db/models.py`
  (`Conversation`: id, title, created_at; `Message`: id,
  conversation_id FK, role, content_json, created_at — both
  `__table_args__ = {"schema": "app"}`).
- **Correction to the previous handoff's claim:** the `app` schema was
  NOT new — `app/catalog/sync.py` and `app/glossary/embed.py` already
  create it (`catalog_tables`, `catalog_columns`, `kb_chunks`). This
  slice's migration is additive alongside those, confirmed by querying
  `information_schema.tables` after `alembic upgrade head`: `app` now
  has `catalog_columns, catalog_embeddings, catalog_tables,
  conversations, kb_chunks, messages` — none of the pre-existing three
  disturbed.
- One hand-written Alembic migration (async template — `alembic init -t
  async`, reusing `app/db/session.py`'s engine directly rather than a
  second URL-building path in `alembic/env.py`) creates `CREATE SCHEMA
  IF NOT EXISTS app` (idempotent) plus both tables. `downgrade()` drops
  only the two tables it created, never the schema.
- The engine uses `poolclass=NullPool`, not the default pool — asyncpg
  connections are event-loop-bound, and this project's per-test-method
  event loops (`unittest.IsolatedAsyncioTestCase`) broke a real pool
  with a live `InterfaceError: another operation is in progress` /
  `Event loop is closed` (reproduced, then fixed by switching pools).
  Flagged in-code to revisit once this pool serves live requests under
  uvicorn's one persistent event loop, where NullPool trades away
  connection reuse.
- A no-slop pre-gate pass caught and fixed a real defect before merge:
  the first draft built the connection DSN via raw f-string
  interpolation of the password, which would have silently mis-parsed
  for any password containing `@`, `:`, `/`, `%`, or `#`. Fixed via
  `URL.create()`, which percent-encodes; verified empirically.
- `tests/test_app_db.py` (7 tests, real, no mocking): model-shape checks
  (exact column sets, engine authenticates as `POSTGRES_USER` not the
  RO role), an insert-then-read-in-a-fresh-session round trip, a nested
  JSON round trip through `content_json`'s JSONB column, a real FK
  violation (`IntegrityError` on a nonexistent `conversation_id`), and a
  cleanup-effectiveness check. Written independently by a test-writer
  subagent from the brief alone, before this implementation existed.
- No `app/main.py`, `app/pipeline/*`, or existing endpoint contract
  touched — this pool is not wired into `/api/ask`/`/api/ask/stream`
  yet. Full suite: 215/215 passing (208 prior + this slice's 7).
- `requirements.txt` gained `sqlalchemy==2.0.51`, `alembic==1.18.5`
  (pinned, installed, proven working). `CLAUDE.md`'s Commands section
  documents `alembic upgrade head`.

## Proof
```
$ .venv/Scripts/alembic.exe upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```
```
$ .venv/Scripts/python.exe -m unittest discover -s tests -p "test_app_db.py" -v
test_conversation_model_has_exactly_the_briefs_columns ... ok
test_engine_authenticates_as_postgres_user ... ok
test_message_model_has_exactly_the_briefs_columns ... ok
test_cleanup_deletes_rows_leaving_no_trace_for_repeat_runs ... ok
test_content_json_round_trips_arbitrary_nested_json ... ok
test_insert_then_read_back_in_a_fresh_session_matches_values ... ok
test_message_with_nonexistent_conversation_id_violates_fk_constraint ... ok

Ran 7 tests in 3.059s

OK
```
Live shipping proof, outside the test suite, against the real dev DB:
inserted a conversation + message, read both back in a fresh session
(`shipping-proof conversation` / `{'q': 'ship it?'}`), listed `app`
schema's tables, deleted both rows, disposed the engine — output and
full gate record in `artifacts/reviews/2026-08-04-app-schema-
persistence.md`. Full suite fresh (pre-fix, unaffected by the later
credential/docstring fixes): `Ran 215 tests in 478.114s / OK`.

## Open questions / known issues
- **This pool is not wired into `/api/ask`/`/api/ask/stream` yet** — the
  next slice, below.
- **What happens to an already-computed answer when its persistence write
  fails, once wiring lands (next slice, below):** for `/api/ask`, an
  uncaught error from the persistence write after a successful
  `get_answer()` call is a plain 500 (correct — the app DB is owned state,
  not an upstream being proxied, so 500 beats 502 here). For
  `/api/ask/stream`, SSE headers are already sent by the time persistence
  runs, so the same failure truncates the stream silently: neither a
  `result` nor an `error` event reaches the client, even though the answer
  was successfully computed. Decided at that slice's Gate 1 to keep this
  behavior rather than add new error-shape handling to paper over it — not
  yet decided whether it needs a real fix (e.g. persist before streaming
  the result event, or a fallback error event if persistence fails after
  the result event was already queued).
- **`NullPool` needs re-evaluation once this pool serves live HTTP
  requests** under uvicorn's single persistent event loop, where a real
  pool (e.g. `AsyncAdaptedQueuePool`) may be worth the connection-reuse
  win now that cross-loop reuse in tests is the only reason NullPool was
  required. Flagged in `app/db/session.py`'s own comment.
- **Real installed Python is 3.11.15** (`.venv`), not the 3.12
  ARCHITECT.md names — newly noticed this session (`python --version`),
  not introduced by this slice, not investigated or acted on.
- **Decimal-valued rows still serialize as JSON strings, not numbers**
  (carried over, unchanged) — both `/api/ask*` endpoints share this via
  `AskResponse` + `jsonable_encoder`. Once persistence is wired in, the
  same rows will be stored in `content_json` in that same string form —
  worth deciding deliberately, not by default, when the next slice
  lands.
- **`plans/logs/_auto-capture.md` remains silently uncommitted across
  every commit** (pre-existing workflow gap, still not decided) — the
  post-commit hook appends to it after *every* commit including the
  "Capture: ..." commit that carries its own prior append, so it's
  dirty again the instant that commit lands. Flagged for 5+ commits now
  with no fix proposed; worth deciding this rather than re-flagging
  again.
- `tests/test_seed_idempotency.py`'s own real Postgres deadlock (M1-era,
  unrelated code) remains uninvestigated.
- The doubled-Voyage-call-per-question design cost
  (`app/pipeline/generate_sql.py`) remains unoptimized — accepted,
  documented in code.
- Lint/type tooling (`ruff`, `mypy`) and the test runner (`unittest`,
  not `pytest`) remain unaddressed, carried over from every prior slice.
- The concurrency-safety pattern (session-scoped advisory locks) is
  still scoped to exactly the two test classes it was applied to.
- Starlette's `TestClient` still emits the `httpx2` deprecation
  warning — harmless, not acted on.
- `Conversation`'s `user_id` FK to `users` is deliberately omitted —
  `users` doesn't exist yet (F8). Documented in `app/db/models.py`'s own
  docstring as a gap to close when F8 lands.

## Next slice (the brief, written NOW while context is hot)
Goal:
Wire `POST /api/ask` and `POST /api/ask/stream` to actually persist a
conversation and its messages through this slice's new pool: each
successful request creates one new `Conversation`, a `user`-role
`Message` holding the question, and an `assistant`-role `Message`
holding the same `{"sql", "rows"}` shape already returned to the client
— proving the HTTP layer and the persistence layer are wired together
end-to-end, not just independently working.

Constraints:
- Use `app/db/session.py`'s existing `async_session_factory` — no new
  pool, no change to `app/db/models.py` or the migration (schema is
  done; this slice only writes through it).
- `execute_sql()`'s read-only asyncpg pool stays completely untouched —
  this is app-state persistence, not generated-SQL execution.
- Persist ONLY on the success path. On any `get_answer()` failure (the
  existing 502 for `/api/ask`, the existing `error` SSE event for
  `/api/ask/stream`), persist nothing — no content_json shape for
  errors has been decided yet, and inventing one is out of scope here.
- Each request creates a brand-new `Conversation` — neither endpoint's
  request body has a way to reference an existing one yet (no
  `conversation_id` field), so continuing a prior conversation across
  requests is explicitly not this slice's job.
- The HTTP response contract for both endpoints stays byte-for-byte
  unchanged (`AskResponse` for `/api/ask`; the existing `result`/`error`
  SSE events for `/api/ask/stream`) — persistence is a side effect, not
  a new field in the response. Returning `conversation_id`/`message_id`
  to the client is deferred to whenever these interim endpoints are
  replaced by PRD.md §8's real API surface.
- Tests hit the real dev Postgres instance for both the HTTP call and
  the persistence check (no mocking the DB); clean up any rows they
  create, mirroring `tests/test_app_db.py`'s pattern.

Inputs:
- `app/main.py` — the two existing endpoints to modify.
- `app/db/session.py` (`async_session_factory`) and `app/db/models.py`
  (`Conversation`, `Message`) — this slice's new pool and models, to
  use as-is.
- `tests/test_api_ask.py` / `tests/test_api_ask_stream.py` — existing
  test conventions (real happy path, mocked-seam failure path) to keep
  intact and extend.
- `tests/test_app_db.py` — the insert/cleanup pattern to mirror for the
  new persistence-check tests.

Outputs:
- `app/main.py`'s `/api/ask` and `/api/ask/stream` handlers each open an
  `async_session_factory()` session, create a `Conversation`, a `user`
  `Message`, and (on success only) an `assistant` `Message`, and commit
  — before returning/streaming the existing response unchanged.
- New test cases (in the existing test files or a new one) asserting
  that a real HTTP call results in exactly one new conversation and two
  new messages in the database, with the expected roles and
  `content_json` shapes, then deletes them.

Done-check:
`python -m unittest discover -s tests -p "test_api_ask*.py" -v` passing,
pasted fresh, in one sitting — covers both `test_api_ask.py` and
`test_api_ask_stream.py`.

Out-of-scope:
- Accepting an existing `conversation_id` in the request body to
  continue a conversation (multi-turn) — future slice.
- Returning `conversation_id`/`message_id` in the HTTP response body —
  future slice, tied to replacing these interim endpoints with PRD.md
  §8's real API surface.
- Persisting anything on the failure/error path.
- `users`/auth (F8); `queries`/`dashboards`/`cards` tables (F6/F7).
- Any change to `app/pipeline/*`, `execute_sql()`'s read-only pool, or
  this slice's migration/models.
- The `NullPool`-under-live-load question, decimal-as-string
  serialization, `_auto-capture.md`'s uncommitted-backlog question,
  `test_seed_idempotency.py`'s deadlock, lint/type tooling (all carried
  over, untouched).
