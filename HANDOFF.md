# Handoff

Date: 2026-08-04
Slice just completed: plans/briefs/2026-08-04-conversations-endpoints.md
  + plans/logs/2026-08-04-conversations-endpoints.md
  (commits 7fa16e7, 2ab5850)

## State of the work
- **`app/main.py` now has PRD.md §8's real conversation-creation and
  multi-turn-messaging endpoints**, alongside the still-unchanged interim
  `/api/ask`/`/api/ask/stream`: `POST /api/conversations` creates one
  empty `Conversation` row and returns `{"id": int}`; `POST
  /api/conversations/{id}/messages` 404s immediately (zero `get_answer()`
  calls, nothing persisted) if `id` doesn't exist, otherwise runs
  `get_answer()`, persists the `user`/`assistant` `Message` pair under
  that exact `conversation_id` via the new `_persist_message_pair()`
  helper, and streams `result`/`error` SSE events where `result`'s data
  is `{"conversation_id", "message_id", "sql", "rows"}` (validated
  through a dedicated `ConversationMessageResult` model, not a raw dict
  merge).
- **Proven end-to-end with a live uvicorn process + curl, verified
  directly in Postgres** — created a conversation, posted a real
  question against it, confirmed both the `user` and `assistant` rows
  landed under that exact `conversation_id`, confirmed the unknown-id
  sentinel (`999999999`) call left zero messages, cleaned up afterward.
- **`_persist_exchange()`/`_ask_stream_events()` (interim endpoints) are
  untouched** — confirmed via diff — and a new `_conversation_message_stream_events()`
  deliberately mirrors `_ask_stream_events()`'s try/except/yield shape
  rather than extracting a shared helper, to keep that guarantee.
- **New test file `tests/test_api_conversations.py`** (18 tests, 3
  scenario classes) proves: a real conversation id round-trips through a
  real `get_answer()` call with exactly 2 messages landing under that
  same `conversation_id`; an unknown sentinel id 404s with the LLM never
  called (a fake that `self.fail()`s if invoked, not a state proxy); a
  failed `get_answer()` call against a real conversation persists
  nothing and still surfaces as an `error` SSE event. All DB assertions
  scope to the exact `conversation_id` each test's own call produced —
  never a newest-row lookup or global count, since the stop_verify hook
  can run this suite concurrently against the live dev DB.
- **A design gap was caught before it ever shipped, and promoted**: the
  first draft of the SSE result payload was a raw
  `{**jsonable_encoder(response), "conversation_id": ..., "message_id":
  ...}` dict merge — a Plan-agent validation pass flagged this as the
  same pattern already named "worth watching" in
  `plans/logs/2026-08-04-fastapi-ask-stream-endpoint.md`'s own log (that
  slice's first draft streamed an unvalidated dict instead of routing
  through `AskResponse`). Fixed with a dedicated
  `ConversationMessageResult` model before implementation began. Now a
  standing `templates/no-slop.md` line (category 7) so future endpoints
  catch this on the first draft.
- Full suite: 247/247 passing (229 prior + 18 new). No regressions.
- `app/db/models.py`, `app/db/session.py`, and all migrations untouched,
  per this slice's own constraint.

## Proof
```
$ .venv/Scripts/python.exe -m unittest discover -s tests -p "test_api_conversations*.py" -v
[... 18 tests across ConversationMessageHappyPathTests,
     UnknownConversationIdTests, ConversationMessageFailurePathTests ...]
----------------------------------------------------------------------
Ran 18 tests in 12.999s

OK
```
```
$ .venv/Scripts/python.exe -m unittest discover -s tests
----------------------------------------------------------------------
Ran 247 tests in 394.926s

OK
```
Live shipping proof (uvicorn + curl, outside the test suite):
```
$ curl -s -X POST http://127.0.0.1:8124/api/conversations
{"id":92}

$ curl -s -X POST http://127.0.0.1:8124/api/conversations/999999999/messages \
    -H "Content-Type: application/json" -d '{"question":"irrelevant"}' -w "\nHTTP %{http_code}\n"
{"detail":"conversation not found"}
HTTP 404

$ curl -s -N -X POST http://127.0.0.1:8124/api/conversations/92/messages \
    -H "Content-Type: application/json" \
    -d '{"question": "How many orders are in the orders table?"}' -w "\nHTTP %{http_code}\n"
event: result
data: {"conversation_id": 92, "message_id": 138, "sql": "SELECT COUNT(*) AS order_count FROM olist.orders", "rows": [{"order_count": 99441}]}

HTTP 200
```
Queried directly in Postgres afterward (separate script, no app/test
code involved):
```
conversation id: 92 created_at: 2026-08-04 16:21:30.332035+00:00
 - user {'question': 'How many orders are in the orders table?'}
 - assistant {'sql': 'SELECT COUNT(*) AS order_count FROM olist.orders', 'rows': [{'order_count': 99441}]}
messages for unknown sentinel id: []
```
Row cleaned up afterward; confirmed gone. Full gate record:
`artifacts/reviews/2026-08-04-conversations-endpoints.md`
(verdict: accept, all five checks green).

## Open questions / known issues
- **No read-back yet**: a client can create a conversation and post
  messages to it, but cannot list conversations or fetch one's history —
  that's the next slice below.
- **What happens to an already-computed answer when its persistence
  write fails**: unchanged from the prior slice's accepted behavior — a
  plain 500 for `/api/ask`, a silently truncated SSE stream for
  `/api/ask/stream` and now `/api/conversations/{id}/messages` too (the
  new `_persist_message_pair()` is deliberately not wrapped in its own
  try/except, same rationale as `_persist_exchange()`). Not yet decided
  whether this needs a real fix.
- **`NullPool` needs re-evaluation once this pool serves live HTTP
  requests** under uvicorn's single persistent event loop — still
  flagged in `app/db/session.py`'s own comment, still not acted on, now
  serving three live endpoints instead of two.
- **Real installed Python is 3.11.15** (`.venv`), not the 3.12
  ARCHITECT.md names — carried over, not investigated or acted on.
- **Decimal-valued rows still serialize as JSON strings, not numbers** —
  carried over unchanged, now also true of `/api/conversations/{id}/messages`'s
  SSE `result` payload (same `AskResponse`/`jsonable_encoder` path).
- **`plans/logs/_auto-capture.md` remains silently uncommitted across
  every commit** (pre-existing workflow gap) — flagged for 7+ commits
  now with no fix proposed. Note: this session also found `HANDOFF.md`
  itself left uncommitted-and-stale across a session boundary (the
  working tree held the *previous* slice's handoff text, uncommitted,
  while two more slices landed on top of it) — same underlying gap,
  worth fixing together if it recurs a third time.
- `tests/test_seed_idempotency.py`'s own real Postgres deadlock (M1-era,
  unrelated code) remains uninvestigated.
- The doubled-Voyage-call-per-question design cost
  (`app/pipeline/generate_sql.py`) remains unoptimized — accepted,
  documented in code.
- Lint/type tooling (`ruff`, `mypy`) and the test runner (`unittest`, not
  `pytest`) remain unaddressed, carried over from every prior slice.
- The concurrency-safety pattern (session-scoped advisory locks) is still
  scoped to exactly the two test classes it was originally applied to —
  unrelated to the newest-row/distinctive-value/exact-id test patterns
  used elsewhere (different mechanism, same underlying hazard family).
- Starlette's `TestClient` still emits the `httpx2` deprecation warning —
  harmless, not acted on.
- `Conversation`'s `user_id` FK to `users` is deliberately omitted —
  `users` doesn't exist yet (F8).

## Next slice (the brief, written NOW while context is hot)
Goal:
Add PRD.md §8's `GET /api/conversations` (list every conversation,
newest first, as `[{"id", "title", "created_at"}, ...]`) and `GET
/api/conversations/{id}` (one conversation's full detail plus its
messages in chronological order, as `{"id", "title", "created_at",
"messages": [{"id", "role", "content_json", "created_at"}, ...]}`,
404 if `id` doesn't exist) — the read-back half of F7, letting a future
chat UI list conversations and reopen one's history.

Constraints:
- Reuse `Conversation`, `Message`, `async_session_factory` exactly as
  they exist — no model or migration changes.
- No pagination, filtering, or sorting options — return everything,
  ordered newest-conversation-first for the list, oldest-message-first
  within a conversation's detail. (Single-tenant demo dataset; revisit
  if it ever gets slow.)
- No user/auth scoping — `users` doesn't exist yet (F8), so this lists
  every conversation in the database, not "mine."
- `title` is returned exactly as stored (`null` today — no title is ever
  set by any endpoint yet) — do not invent or backfill one.
- `content_json` is returned exactly as persisted, no reshaping.
- `/api/ask`, `/api/ask/stream`, `POST /api/conversations`, and `POST
  /api/conversations/{id}/messages` stay byte-for-byte unchanged — this
  slice only adds the two new `GET` routes.
- No new dependencies.
- Tests hit the real dev Postgres instance (create real conversations
  via the existing `POST` endpoints, then `GET` them back — no mocking
  the DB). Per `templates/no-slop.md` category 5: the list endpoint's
  test must assert *membership* (the conversation this test created is
  present in the returned list, by its own id) rather than an exact
  count or length, since the stop_verify hook can run this suite
  concurrently against the same live table and other conversations may
  exist at any time. The detail endpoint's test can assert exactly,
  scoped by the specific id it created.

Inputs:
- `app/main.py` — where the two new routes are added; reuse
  `Conversation`/`Message`/`async_session_factory` imports already there.
- `tests/test_api_conversations.py` — the existing `POST` endpoints to
  create real fixtures for these `GET` tests to read back; its async
  DB-helper-via-`asyncio.run()` and cleanup conventions to reuse or
  extend.
- PRD.md §8 and §7 — the exact route shapes and the `conversations`/
  `messages` column names.

Outputs:
- `app/main.py` gains `GET /api/conversations` and `GET
  /api/conversations/{id}` (404 on unknown id, matching the existing
  `session.get(Conversation, id)` convention from `post_conversation_message`).
- A new test file (e.g. `tests/test_api_conversations_read.py`) proving:
  a conversation created via `POST /api/conversations` appears in `GET
  /api/conversations`'s list by id (membership check, not count); `GET
  /api/conversations/{id}` for a real conversation with real messages
  (created via `POST /api/conversations/{id}/messages`) returns those
  messages in the right order with the right shape; `GET
  /api/conversations/{id}` for an unknown id returns a real 404.

Done-check:
`python -m unittest discover -s tests -p "test_api_conversations_read*.py" -v`
passing, pasted fresh, in one sitting.

Out-of-scope:
- Pagination, filtering, sorting options.
- Conversation titles (auto-titling, editing) — stays `null`.
- Auth/user scoping (`POST /api/auth/login`/`logout`, "my conversations
  only") — F8, `users` table doesn't exist yet.
- Deleting or renaming conversations.
- Dashboards/cards endpoints (F6/F7's other half).
- Any frontend/UI work consuming these endpoints (M5).
- Fixing the stream-truncation-on-persist-failure gap, the `NullPool`
  question, decimal-as-string serialization, `_auto-capture.md`'s
  uncommitted-backlog question, `test_seed_idempotency.py`'s deadlock,
  lint/type tooling (all carried over, untouched).
