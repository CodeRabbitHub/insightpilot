# Slice log — conversations-endpoints

Date: 2026-08-04
Brief: plans/briefs/2026-08-04-conversations-endpoints.md

## The plan you approved
Add `POST /api/conversations` (empty conversation → `{"id"}`) and
`POST /api/conversations/{id}/messages` (404-before-any-LLM-call on an
unknown id, otherwise runs `get_answer()` and persists against that
existing conversation, streaming SSE `result`/`error` with
`conversation_id`/`message_id` included) to `app/main.py`, reusing
`get_answer()`/`async_session_factory`/`Conversation`/`Message` exactly
as-is — no model/migration changes, `/api/ask`/`/api/ask/stream`
untouched. A Plan-agent validation pass caught one design gap before
implementation: the SSE result payload should route through a dedicated
Pydantic model (`ConversationMessageResult`), not a raw
`{**jsonable_encoder(response), ...}` dict merge.

## The diff you accepted
Commit `7fa16e7` — "Add POST /api/conversations and
POST /api/conversations/{id}/messages". `app/main.py` +99 lines (2
response models, 2 routes, 2 helpers); new `tests/test_api_conversations.py`
(528 lines, 18 tests, 3 scenario classes); new brief; new gate record.
Full stat: `plans/logs/_auto-capture.md`'s next append (post-commit hook).

## The done-check output
```
$ .venv/Scripts/python.exe -m unittest discover -s tests -p "test_api_conversations*.py" -v
...
Ran 18 tests in 12.999s

OK
```
Full suite (regression check, not the literal done-check):
```
$ .venv/Scripts/python.exe -m unittest discover -s tests
Ran 247 tests in 394.654s

OK
```
Live shipping proof (uvicorn + curl, outside the test suite), queried
directly in Postgres afterward — see
`artifacts/reviews/2026-08-04-conversations-endpoints.md` for the full
transcript. Row cleaned up afterward; confirmed gone.

## One thing you rejected or changed
Two things, both caught by process, not rubber-stamped:

1. **A Plan-agent validation pass caught a real design gap before any
   code was written**: my first draft built the SSE result payload as
   `{**jsonable_encoder(response), "conversation_id": ..., "message_id": ...}`
   — a raw dict merge. This repeats, almost exactly, the pattern flagged
   in `plans/logs/2026-08-04-fastapi-ask-stream-endpoint.md`'s own "one
   thing rejected" section: that slice's first draft streamed
   `get_answer()`'s output as an unvalidated dict instead of routing it
   through `AskResponse`, and that log explicitly said "worth watching:
   any future endpoint that serializes by hand... " This is that
   watched-for second occurrence. Fixed by adding a dedicated
   `ConversationMessageResult` Pydantic model before implementation
   began — caught at the design stage, never actually shipped. **Promoted**:
   added a new bullet to `templates/no-slop.md` category 7 naming both
   occurrences, so future reviews catch this on the first draft, not the
   second.
2. **no-slop pre-gate (two passes)** found two more fixable findings:
   `_persist_message` renamed to `_persist_message_pair` (its name didn't
   signal it persists two rows, unlike `_persist_exchange`'s equivalent
   clarity), and `_conversation_message_stream_events`'s docstring didn't
   explain why it deliberately mirrors `_ask_stream_events`'s
   try/except/yield structure instead of extracting a shared helper
   (`/api/ask/stream` must stay byte-for-byte unchanged this slice, so
   its generator was left untouched rather than refactored). Both fixed;
   re-verified clean by the second pass. Two lower-severity duplication
   findings (the `Conversation`-creation sequence and the
   `Message`-pair-construction shape both partially duplicating
   `_persist_exchange()`) were reviewed and explicitly accepted — the
   brief's own Inputs section anticipated needing "a variant," and
   extracting a shared helper would risk touching the
   byte-for-byte-unchanged `/api/ask` path for marginal benefit.

## The next smallest slice
`GET /api/conversations` (list) and `GET /api/conversations/{id}`
(read-back with its messages) — the explicit out-of-scope carry-over
from this brief, needed before any chat UI (M5) can show conversation
history or resume an existing conversation.
