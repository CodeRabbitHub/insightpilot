# Brief — wire persistence into /api/ask endpoints

Date: 2026-08-04
Milestone: M4 API (FastAPI endpoints, SSE streaming, conversations/messages
persisted in the app schema)

Goal:
Each successful `POST /api/ask` or `POST /api/ask/stream` request persists
one new `Conversation`, a `user`-role `Message` holding the question, and an
`assistant`-role `Message` holding the same `{"sql", "rows"}` shape already
returned to the client — proving the HTTP layer and the persistence layer
(from the prior slice) are wired together end-to-end.

Constraints:
- Use `app/db/session.py`'s existing `async_session_factory` only — no new
  pool, no change to `app/db/models.py` or the Alembic migration (schema is
  done; this slice only writes through it).
- `execute_sql()`'s read-only asyncpg pool stays completely untouched — this
  is app-state persistence, not generated-SQL execution.
- Persist ONLY on the success path. On any `get_answer()` failure (the
  existing 502 for `/api/ask`, the existing `error` SSE event for
  `/api/ask/stream`), persist nothing — no content_json shape for errors has
  been decided yet, and inventing one is out of scope here.
- Each request creates a brand-new `Conversation` — neither endpoint's
  request body has a `conversation_id` field yet, so continuing a prior
  conversation across requests is explicitly not this slice's job.
- The HTTP response contract for both endpoints stays byte-for-byte
  unchanged (`AskResponse` for `/api/ask`; the existing `result`/`error` SSE
  events for `/api/ask/stream`) — persistence is a side effect, not a new
  response field.
- Tests hit the real dev Postgres instance for both the HTTP call and the
  persistence check (no mocking the DB); clean up any rows they create,
  mirroring `tests/test_app_db.py`'s pattern.
- Tests must not assume they are the only writer to `app.conversations`/
  `app.messages` — the stop_verify hook can run this same suite concurrently
  with a manual run against the real dev DB. So:
  - Happy-path checks identify the row this call created by querying the
    single newest conversation (`ORDER BY id DESC LIMIT 1`) and its two
    messages, not by snapshotting a max-id/count before the call and
    asserting an exact diff of "one new row" — a concurrent writer between
    the snapshot and the check breaks that count.
  - Failure-path checks (persist-nothing-on-error) use a distinctive
    question string unique to that test (not a shared literal like
    "irrelevant for this test") and assert no message with that exact
    `content_json` exists — scoped to the exchange this specific call would
    have created, not "no new conversation exists at all," which a
    concurrently-running happy-path test would trip.
- An uncaught persistence error after a successful `get_answer()` call is
  not handled specially this slice: for `/api/ask` it surfaces as a plain
  500 (the DB is app-owned state, not an upstream being proxied, so 500 is
  correct — not 502). For `/api/ask/stream`, SSE headers are already sent by
  that point, so the same failure truncates the stream with neither a
  `result` nor an `error` event reaching the client. Keep this behavior;
  do not add new error-shape handling to paper over it (out of scope).

Inputs:
- `app/main.py` — the two existing endpoints to modify.
- `app/db/session.py` (`async_session_factory`) and `app/db/models.py`
  (`Conversation`, `Message`) — this slice's pool and models, used as-is.
- `tests/test_api_ask.py` / `tests/test_api_ask_stream.py` — existing test
  conventions (real happy path, mocked-seam failure path) to keep intact and
  extend.
- `tests/test_app_db.py` — the insert/cleanup pattern to mirror for the new
  persistence-check tests.

Outputs:
- `app/main.py`'s `/api/ask` and `/api/ask/stream` handlers each open an
  `async_session_factory()` session, create a `Conversation`, a `user`
  `Message`, and (on success only) an `assistant` `Message`, and commit —
  before returning/streaming the existing response unchanged.
- New test cases (in the existing test files or a new one) asserting that a
  real HTTP call's exchange is found in the database as the newest
  conversation plus its two messages, with the expected roles and
  `content_json` shapes (per the concurrency-safe lookup above), then
  deletes them.

Done-check:
`python -m unittest discover -s tests -p "test_api_ask*.py" -v` passing,
pasted fresh, in one sitting — covers both `test_api_ask.py` and
`test_api_ask_stream.py`.

Out-of-scope:
- Accepting an existing `conversation_id` in the request body to continue a
  conversation (multi-turn) — future slice.
- Returning `conversation_id`/`message_id` in the HTTP response body —
  future slice, tied to replacing these interim endpoints with PRD.md §8's
  real API surface.
- Persisting anything on the failure/error path.
- `users`/auth (F8); `queries`/`dashboards`/`cards` tables (F6/F7).
- Any change to `app/pipeline/*`, `execute_sql()`'s read-only pool, or the
  prior slice's migration/models.
- The `NullPool`-under-live-load question, decimal-as-string serialization,
  `_auto-capture.md`'s uncommitted-backlog question,
  `test_seed_idempotency.py`'s deadlock, lint/type tooling (all carried
  over, untouched).
