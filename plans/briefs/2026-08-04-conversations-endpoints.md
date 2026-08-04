# Brief — conversations-endpoints

Date: 2026-08-04
Milestone: M4 (API: FastAPI endpoints, SSE streaming, persistence of
conversations/messages) — PRD.md §8

Goal:
Add PRD.md §8's real `POST /api/conversations` (create an empty
conversation, returns `{"id": int}`) and `POST /api/conversations/{id}/messages`
(accepts `{"question": str}` for an *existing* conversation, runs the same
`get_answer()` pipeline, persists both messages under that
`conversation_id`, and streams the result as SSE with `conversation_id`
and `message_id` included) — enabling real multi-turn conversations,
which the interim endpoints' always-brand-new-conversation design cannot.

Constraints:
- Reuse `get_answer()`, `async_session_factory`, `Conversation`, and
  `Message` exactly as they exist — no pipeline, model, or migration
  changes.
- `POST /api/conversations/{id}/messages` must check that `id` refers to
  a real conversation *before* calling `get_answer()` — an unknown id
  returns 404 immediately, with no LLM call and nothing persisted. Do not
  waste a real Anthropic call validating a path parameter.
- Persist-only-on-success stays exactly as the prior slice decided: on
  any `get_answer()` failure, persist nothing; the same accepted
  behavior for an uncaught persistence-write failure (500-shaped / stream
  truncation) carries forward unchanged — not this slice's job to fix.
- `content_json` stays exactly `{"question": ...}` / `{"sql": ...,
  "rows": ...}` — no `chart_spec`/`summary`/`explanation`/`follow_ups`
  enrichment; that's M5's `analyze.md` prompt step, not built yet.
- `/api/ask` and `/api/ask/stream` stay byte-for-byte unchanged — this
  slice adds the new pair alongside them, it does not remove or modify
  the interim endpoints.
- Tests hit the real dev Postgres instance and the real pipeline for
  happy paths (no mocking the DB or LLM), matching this repo's existing
  convention. Per `templates/no-slop.md` category 5: DB assertions must
  scope to the specific conversation/message this test's own call
  created (by the id/content it just got back), never a
  snapshot-then-diff or global-count check, since the stop_verify hook
  can run this suite concurrently with a manual run.
- No new dependencies (CLAUDE.md standing rule).

Inputs:
- `app/main.py` — where the two new routes are added.
- `app/db/session.py` (`async_session_factory`), `app/db/models.py`
  (`Conversation`, `Message`) — used as-is.
- `app/main.py`'s existing `_persist_exchange()` and `_ask_stream_events()`
  — the persistence and SSE-yielding logic to adapt (it currently always
  creates a new `Conversation`; this slice needs a variant that persists
  against an *existing* one and returns the created message's id).
- `tests/test_api_ask_persistence.py` — the concurrency-safe DB-assertion
  pattern (newest-row lookup, distinctive-question absence check) to
  reuse for the new endpoints' tests.
- `tests/test_api_ask_stream.py` — the hand-rolled SSE-parsing helper and
  real-pipeline/mocked-failure test conventions to follow for the new
  streaming endpoint.
- PRD.md §8 — the exact route shapes (`POST /api/conversations`,
  `POST /api/conversations/{id}/messages` → SSE).

Outputs:
- `app/main.py` gains `POST /api/conversations` (creates one
  `Conversation` row with no title, returns `{"id": conversation.id}`)
  and `POST /api/conversations/{id}/messages` (404s on an unknown `id`;
  otherwise runs `get_answer()`, persists the `user`/`assistant` message
  pair under that `id`, and streams `result`/`error` SSE events where
  `result`'s data is `{"conversation_id", "message_id", "sql", "rows"}`).
- New test file `tests/test_api_conversations.py` proving: a real
  created conversation's id is usable to post a real question and get a
  real streamed answer back, with the persisted rows landing under that
  same conversation_id (not a new one); posting to a nonexistent
  conversation_id returns a real 404 with nothing persisted; a failed
  `get_answer()` call against a real conversation persists nothing and
  still surfaces as an `error` SSE event.

Done-check:
`python -m unittest discover -s tests -p "test_api_conversations*.py" -v`
passing, pasted fresh, in one sitting.

Out-of-scope:
- `GET /api/conversations` (list) and `GET /api/conversations/{id}`
  (history/read-back) — future slice.
- Auth (`POST /api/auth/login`/`logout`) — F8, `users` table doesn't
  exist yet.
- Removing or deprecating the interim `/api/ask` / `/api/ask/stream`
  endpoints — a separate decision once something actually migrates to
  the new surface.
- Dashboards/cards endpoints (F6/F7).
- Conversation titles (auto-titling, editing) — stays `null` this slice.
- Fixing the stream-truncation-on-persist-failure gap, the `NullPool`
  question, decimal-as-string serialization, `_auto-capture.md`'s
  uncommitted-backlog question, `test_seed_idempotency.py`'s deadlock,
  lint/type tooling (all carried over, untouched).
