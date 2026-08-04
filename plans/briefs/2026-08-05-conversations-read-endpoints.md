# Brief — conversations-read-endpoints

Date: 2026-08-05
Milestone: M4 (API: FastAPI endpoints, SSE streaming, persistence of
conversations/messages) — PRD.md §8

Goal:
Add PRD.md §8's read-back pair — `GET /api/conversations` (every
conversation, newest first, as `[{"id", "title", "created_at"}, ...]`)
and `GET /api/conversations/{id}` (one conversation's full detail plus
its messages in chronological order, as `{"id", "title", "created_at",
"messages": [{"id", "role", "content_json", "created_at"}, ...]}`, 404
on an unknown id) — so a client can list conversations and reopen one's
history, completing F7's read side against the existing `POST`
endpoints.

Constraints:
- Reuse `Conversation`, `Message`, `async_session_factory` exactly as
  they exist — no model or migration changes.
- No pagination, filtering, or sorting options — return everything,
  newest-conversation-first for the list, oldest-message-first within a
  conversation's detail. (Single-tenant demo dataset; revisit if it ever
  gets slow.)
- No user/auth scoping — `users` doesn't exist yet (F8), so this lists
  every conversation in the database, not "mine."
- `title` is returned exactly as stored (`null` today — no endpoint sets
  one yet) — do not invent or backfill one.
- `content_json` is returned exactly as persisted, no reshaping.
- `/api/ask`, `/api/ask/stream`, `POST /api/conversations`, and
  `POST /api/conversations/{id}/messages` stay byte-for-byte unchanged —
  this slice only adds the two new `GET` routes.
- No new dependencies (CLAUDE.md standing rule).
- Tests hit the real dev Postgres instance (create real conversations via
  the existing `POST` endpoints, then `GET` them back — no mocking the
  DB). Per `templates/no-slop.md` category 5: the list endpoint's test
  must assert *membership* (the conversation this test created is present
  in the returned list, by its own id) rather than an exact count or
  length, since the stop_verify hook can run this suite concurrently
  against the same live table and other conversations may exist at any
  time. The detail endpoint's test can assert exactly, scoped by the
  specific id it created.

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
- `app/main.py` gains `GET /api/conversations` and
  `GET /api/conversations/{id}` (404 on unknown id, matching the existing
  `session.get(Conversation, id)` convention from
  `post_conversation_message`).
- A new test file `tests/test_api_conversations_read.py` proving: a
  conversation created via `POST /api/conversations` appears in
  `GET /api/conversations`'s list by id (membership check, not count);
  `GET /api/conversations/{id}` for a real conversation with real
  messages (created via `POST /api/conversations/{id}/messages`) returns
  those messages in the right order with the right shape; `GET
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
