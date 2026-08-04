# Review gate — conversations-read-endpoints

Date: 2026-08-05
Brief: plans/briefs/2026-08-05-conversations-read-endpoints.md
Diff reviewed: working tree — app/main.py (modified), tests/test_api_conversations_read.py (new), plans/briefs/2026-08-05-conversations-read-endpoints.md (new)

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review
`git diff --stat -- app/main.py`:
```
app/main.py | 70 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
1 file changed, 70 insertions(+)
```
Plus two new files: tests/test_api_conversations_read.py (601 lines, 23
tests, entirely test code following this repo's existing per-class
conventions) and the brief itself (81 lines). Every line was read.
**PASS.**

## 2. The stated goal matches the actual change
Brief's Goal: add `GET /api/conversations` (list, newest first, as
`[{"id","title","created_at"}, ...]`) and `GET /api/conversations/{id}`
(detail + messages in chronological order, 404 on unknown id). The diff
adds exactly these two routes plus three supporting Pydantic models
(`ConversationSummary`, `MessageDetail`, `ConversationDetail`), matching
the existing per-route explicit-model convention
(`CreateConversationResponse`, `ConversationMessageResult`). No changes
to `/api/ask`, `/api/ask/stream`, or the two existing `POST` conversation
routes — confirmed via diff (additions only, no deletions elsewhere). No
extra "improvements" smuggled in (no pagination, no title logic, no auth).
**PASS.**

## 3. The eval or test passed
No LLM-behavior/prompt changes in this slice, so no eval run required.
Done-check run fresh:
```
$ .venv/Scripts/python.exe -m unittest discover -s tests -p "test_api_conversations_read*.py" -v
[... 23 tests: ConversationDetailTests (13), ConversationDetailWithNoMessagesTests (2),
     ConversationListMembershipTests (5), ConversationListOrderingTests (1),
     UnknownConversationIdDetailTests (1) ...]
----------------------------------------------------------------------
Ran 23 tests in 9.310s

OK
```
Full suite also run fresh (no regressions):
```
$ .venv/Scripts/python.exe -m unittest discover -s tests
----------------------------------------------------------------------
Ran 268 tests in 293.800s

OK
```
(247 prior + 21 read-endpoint tests captured before the zero-messages
addition; the 23-test number above is the final count after that
addition — full suite re-run not repeated a second time since the
addition only adds 2 pure-Python test methods with no app-code change.)
**PASS.**

## 4. The no-slop review found no unresolved issues
First pass found one real finding: `GET /api/conversations/{id}` for a
conversation with zero persisted messages (the state right after `POST
/api/conversations`, before any message is posted) was untested — a
trivially reachable, real code path, not a made-up edge. Fixed by adding
`ConversationDetailWithNoMessagesTests` (2 tests: 200 not 404, empty
`messages` list).

Second pass (after the fix) found one more: the module docstring's
per-class summary omitted the newly-added
`ConversationDetailWithNoMessagesTests`, leaving a stale/incomplete
comment. Fixed by adding its paragraph to the docstring.

Re-verified: both fixes present, done-check re-run green (23/23, output
above includes both new test names passing). No unresolved findings
remain. Accepted, already-justified patterns from the review (test-helper
duplication per this repo's per-file convention, `Message.id`-based
ordering matching sibling test/route code) required no further action.
**PASS.**

## 5. The shipping proof is attached
Live uvicorn instance (throwaway, port 8125, stopped and cleaned up
afterward — not part of any persistent dev environment):
```
$ curl -s -X POST http://127.0.0.1:8125/api/conversations
{"id":151}

$ curl -s http://127.0.0.1:8125/api/conversations | python -c "..."
total in list: 21
A in list: True
first item (newest): {'id': 151, 'title': None, 'created_at': '2026-08-04T22:37:57.374433Z'}

$ curl -s http://127.0.0.1:8125/api/conversations/151 -w "\nHTTP %{http_code}\n"
{"id":151,"title":null,"created_at":"2026-08-04T22:37:57.374433Z","messages":[]}
HTTP 200

$ curl -s -N -X POST http://127.0.0.1:8125/api/conversations/151/messages \
    -H "Content-Type: application/json" \
    -d '{"question": "How many orders are in the orders table?"}'
event: result
data: {"conversation_id": 151, "message_id": 196, "sql": "SELECT COUNT(*) FROM olist.orders", "rows": [{"count": 99441}]}

$ curl -s http://127.0.0.1:8125/api/conversations/151 -w "\nHTTP %{http_code}\n"
{"id":151,"title":null,"created_at":"2026-08-04T22:37:57.374433Z","messages":[{"id":195,"role":"user","content_json":{"question":"How many orders are in the orders table?"},"created_at":"2026-08-04T22:38:00.773960Z"},{"id":196,"role":"assistant","content_json":{"sql":"SELECT COUNT(*) FROM olist.orders","rows":[{"count":99441}]},"created_at":"2026-08-04T22:38:00.773960Z"}]}
HTTP 200

$ curl -s http://127.0.0.1:8125/api/conversations/999999999 -w "\nHTTP %{http_code}\n"
{"detail":"conversation not found"}
HTTP 404
```
Demo conversation (id 151) and its two messages deleted afterward via a
direct DB script; confirmed gone. Throwaway server process stopped and
port 8125 confirmed no longer listening.
**PASS.**

## Rejected or changed
- One no-slop finding fixed before merge: the zero-messages detail case
  was untested — added `ConversationDetailWithNoMessagesTests` (2 tests).
- One follow-up no-slop finding fixed: the module docstring was left
  stale (didn't mention the new test class) — added its paragraph.
- Nothing else was rejected; the implementation as planned matched the
  brief on the first pass.

## Verdict
**accept** — all five checks green.
