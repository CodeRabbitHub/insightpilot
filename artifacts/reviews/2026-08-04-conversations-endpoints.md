# Review gate — conversations-endpoints

Date: 2026-08-04
Brief: plans/briefs/2026-08-04-conversations-endpoints.md
Diff reviewed: working tree vs HEAD (dcededb) — `app/main.py`,
`tests/test_api_conversations.py` (new), `plans/briefs/2026-08-04-conversations-endpoints.md` (new)

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review
`app/main.py`: +95 lines (2 new response models, 2 new routes, 2 new
helpers). New test file `tests/test_api_conversations.py`: 528 lines.
New brief: 92 lines. Fully read line by line; reviewable as one slice.

Note: `HANDOFF.md` and `plans/logs/_auto-capture.md` show as modified in
`git status`, but that predates this session (visible in the initial git
status snapshot) — leftover from the prior slice's handoff/capture
bookkeeping gap, already flagged in HANDOFF.md's own Open Questions.
Not part of this slice's diff; left untouched.

## 2. The stated goal matches the actual change
Brief's goal: add `POST /api/conversations` (create empty conversation →
`{"id"}`) and `POST /api/conversations/{id}/messages` (404 before any
LLM call on an unknown id; otherwise runs `get_answer()`, persists both
messages under that conversation, streams SSE `result`/`error` with
`conversation_id`/`message_id` included) — enabling real multi-turn
conversations.

Diff does exactly this and nothing more: two routes, two response
models (`CreateConversationResponse`, `ConversationMessageResult`), two
helpers (`_persist_message_pair`, `_conversation_message_stream_events`).
No title/chart_spec/dashboard additions, no touch to `/api/ask` or
`/api/ask/stream`. Match confirmed both directions.

## 3. The eval or test passed
Done-check, run fresh:
```
$ .venv/Scripts/python.exe -m unittest discover -s tests -p "test_api_conversations*.py" -v
...
Ran 18 tests in 12.999s

OK
```
Full suite (no regressions), run fresh:
```
$ .venv/Scripts/python.exe -m unittest discover -s tests
Ran 247 tests in 394.654s

OK
```
(229 prior + 18 new = 247.)

## 4. The no-slop review found no unresolved issues
Two no-slop-reviewer passes. First pass found 3 findings; all addressed
before the second pass:
- `_persist_message` (now `_persist_message_pair`) renamed — its name
  didn't signal it persists a *pair* of messages, unlike
  `_persist_exchange`'s equivalent clarity. Fixed.
- `_persist_message_pair`'s docstring didn't restate the
  uncaught-write-failure rationale `_persist_exchange` documents. Fixed
  — one sentence added, same reasoning.
- (Accepted, not fixed) `create_conversation()`'s Conversation-creation
  sequence and `_persist_message_pair`'s Message-construction shape both
  duplicate parts of `_persist_exchange()` — the brief's own Inputs
  section anticipated needing "a variant," and refactoring into a shared
  helper would risk touching the byte-for-byte-unchanged `/api/ask` path
  for marginal benefit. Accepted as-is.

Second pass (re-review) found 2 more, both fixed:
- `_conversation_message_stream_events()` duplicated
  `_ask_stream_events()`'s try/except/yield structure with no written
  line explaining the non-extraction. Fixed — docstring now states this
  explicitly (mirrors deliberately, not extracted, to keep
  `/api/ask/stream` untouched).
- (Already covered above) naming fix confirmed resolved on re-check.

Zero unresolved findings after the second pass. Confirmed via
`git diff` by the reviewer itself, not by my summary.

## 5. The shipping proof is attached
Live uvicorn (post-fix code) + curl, then verified directly in Postgres
(separate script, no app/test code involved):
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
Postgres, queried directly afterward:
```
conversation id: 92 created_at: 2026-08-04 16:21:30.332035+00:00
 - user {'question': 'How many orders are in the orders table?'}
 - assistant {'sql': 'SELECT COUNT(*) AS order_count FROM olist.orders', 'rows': [{'order_count': 99441}]}
messages for unknown sentinel id: []
```
Row cleaned up afterward; confirmed gone (`confirmed gone: True`).

## Rejected or changed
- Renamed `_persist_message` → `_persist_message_pair` (no-slop finding).
- Added a docstring line to `_persist_message_pair` restating the
  uncaught-write-failure rationale (no-slop finding).
- Added a docstring line to `_conversation_message_stream_events`
  explaining the deliberate non-extraction from `_ask_stream_events`
  (no-slop finding, second pass).
- Nothing else changed; the `Conversation`-creation and
  `Message`-pair-construction duplication with `_persist_exchange` was
  reviewed and explicitly accepted (see Check 4).

## Verdict
Accept. All five checks green.
