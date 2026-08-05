# Slice log — conversations-read-endpoints

Date: 2026-08-05
Brief: plans/briefs/2026-08-05-conversations-read-endpoints.md

## The plan you approved
Add `GET /api/conversations` (list, newest-first, `created_at` desc +
`id` desc tiebreak) and `GET /api/conversations/{id}` (detail + messages
chronological, 404 on unknown id) to `app/main.py`, each with a dedicated
Pydantic response model (`ConversationSummary`, `MessageDetail`,
`ConversationDetail`), reusing `Conversation`/`Message`/
`async_session_factory` exactly as they exist. Pure reads — no
`get_answer()`, no SSE. Existing routes untouched.

## The diff you accepted
Commit `c7e4700` — "Add GET /api/conversations and GET
/api/conversations/{id}". `app/main.py` (+70), plus the new brief, gate
record, and `tests/test_api_conversations_read.py` (23 tests). Mechanics
in `plans/logs/_auto-capture.md`.

## The done-check output
```
$ .venv/Scripts/python.exe -m unittest discover -s tests -p "test_api_conversations_read*.py" -v
[... 23 tests across ConversationDetailTests, ConversationDetailWithNoMessagesTests,
     ConversationListMembershipTests, ConversationListOrderingTests,
     UnknownConversationIdDetailTests ...]
----------------------------------------------------------------------
Ran 23 tests in 9.310s

OK
```
Full suite re-run clean: 268/268 (247 prior + 21 read-endpoint tests
captured at that checkpoint; 2 more pure-Python test methods were added
after, with no app-code change, per the no-slop fix below).

## One thing you rejected or changed
The no-slop-reviewer pre-gate pass (not the test-writer, not me) found a
real, trivially-reachable untested edge: `GET /api/conversations/{id}`
for a conversation that exists but has zero messages yet (the state
right after `POST /api/conversations`, before any message is posted) —
the code path (`messages = []`) was plausible but unverified. Fixed by
adding `ConversationDetailWithNoMessagesTests` (2 tests: 200 not 404,
`messages == []`). A second no-slop pass then caught that the new test
file's module docstring hadn't been updated to mention that new class —
a stale comment describing code that had changed. Fixed by adding its
paragraph.

This is not a new pattern — it's `templates/no-slop.md`'s "Untested
edges" category (promoted from `2026-08-02-catalog-sync-cli.md`) working
exactly as designed a second time. No further promotion needed.

## The next smallest slice
Bootstrap the M5 React/Vite chat scaffold: a minimal chat page that lists
conversations via `GET /api/conversations`, opens one via `GET
/api/conversations/{id}`, and posts a new message via `POST
/api/conversations/{id}/messages` (consuming its SSE `result`/`error`
events) — the first frontend slice, proving the read/write API surface
built across the last three slices end-to-end from a real browser.
