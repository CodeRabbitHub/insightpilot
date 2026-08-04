# Review gate — wire persistence into /api/ask endpoints

Date: 2026-08-04
Brief: plans/briefs/2026-08-04-wire-persistence-into-ask-endpoints.md
Diff reviewed: working tree vs main (HANDOFF.md, app/main.py, plus new
plans/briefs/2026-08-04-wire-persistence-into-ask-endpoints.md and
tests/test_api_ask_persistence.py)

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review
`git diff --stat` (with the two new files staged via `git add -N` so they
show):
```
 HANDOFF.md                                         |  13 +
 app/main.py                                        |  36 +-
 plans/briefs/2026-08-04-wire-persistence-into-ask-endpoints.md |  95 ++++
 tests/test_api_ask_persistence.py                  | 506 +++++++++++++++++++++
 4 files changed, 649 insertions(+), 1 deletion(-)
```
The actual *implementation* diff is small: `app/main.py` +36/-1 (one new
`_persist_exchange` helper, two one-line call sites) and a 13-line
`HANDOFF.md` addition. The 506-line test file and 95-line brief are new,
not modified, and both were read in full line-by-line during planning and
pre-gate (test-writer's output was read and checked against the brief's
concurrency-safety instructions before implementation began). PASS.

## 2. The stated goal matches the actual change
Brief's Goal: each successful `POST /api/ask` or `POST /api/ask/stream`
request persists one new `Conversation`, a `user` `Message` (the
question), and an `assistant` `Message` (the same `{"sql","rows"}` shape
returned to the client), through the existing `async_session_factory`
pool.

The diff does exactly this and nothing more: `_persist_exchange()` in
`app/main.py` opens one session, creates a `Conversation`, flushes for its
id, adds the two `Message`s, commits — called once from `/api/ask` after
`AskResponse` is built (post-`try/except`, so it never fires on the 502
path) and once from `_ask_stream_events` after the SSE `response` is built
(the `except` branch returns before reaching that line, so the `error`
path never persists). No new pool, no model/migration change, no response
field added, no `conversation_id` request-body field. PASS.

## 3. The eval or test passed
Done-check, run fresh:
```
$ .venv/Scripts/python.exe -m unittest discover -s tests -p "test_api_ask*.py" -v
[... 32 tests ...]
----------------------------------------------------------------------
Ran 32 tests in 50.614s

OK
```
Full suite (no regressions):
```
$ .venv/Scripts/python.exe -m unittest discover -s tests
----------------------------------------------------------------------
Ran 229 tests in 545.926s

OK
```
(229 = 215 from the prior slice + 14 new in `test_api_ask_persistence.py`.)
PASS.

## 4. The no-slop review found no unresolved issues
no-slop-reviewer subagent ran read-only against the diff. Two findings,
both resolved:
- **Stale docstring** (`tests/test_api_ask_persistence.py`): claimed
  "app/main.py has not been modified yet," no longer true once the
  implementation landed alongside it. Fixed — rewritten to describe the
  file's actual history instead of asserting a state the diff falsifies.
- **`_parse_sse_events` duplicated** from `test_api_ask_stream.py`: flagged
  as only the 2nd occurrence of this helper (this repo's own ratchet rule
  is 3rd-occurrence-means-extract), so left as-is rather than extracting
  prematurely — noted as an accepted exception, not a defect.
No other findings across the ten categories; the deliberate "no special
handling for a persistence write failure" decision (500 for `/api/ask`,
truncated stream for `/api/ask/stream`) was confirmed as matching the
brief's explicit Gate-1 instruction, not an oversight. PASS.

## 5. The shipping proof is attached
Ran the real app under uvicorn (not the test suite) and hit it with curl:
```
$ .venv/Scripts/python.exe -m uvicorn app.main:app --port 8123 &
INFO:     Uvicorn running on http://127.0.0.1:8123

$ curl -s -X POST http://127.0.0.1:8123/api/ask -H "Content-Type: application/json" \
    -d '{"question": "How many orders are in the orders table?"}' -w "HTTP %{http_code}\n"
HTTP 200
{"sql":"SELECT COUNT(*) FROM olist.orders","rows":[{"count":99441}]}
```
Then queried Postgres directly (a separate script, outside the app
process and outside the test suite) to confirm the write landed:
```
conversation id: 62 created_at: 2026-08-04 14:43:23.188692+00:00
 - user {'question': 'How many orders are in the orders table?'}
 - assistant {'sql': 'SELECT COUNT(*) FROM olist.orders', 'rows': [{'count': 99441}]}
```
Matches the live HTTP response exactly. Row cleaned up afterward (deleted
message then conversation in separate commits); confirmed gone:
```
post-cleanup conversation: None messages: []
```
Server process terminated (port 8123 confirmed free). PASS.

## Rejected or changed
- Rejected the original plan's test-identification strategy (snapshot
  max-id/count before the call, assert an exact diff of "one new row") at
  Gate 1 — it assumes no concurrent writer to `app.conversations`, which
  is false: the stop_verify hook can run this same suite concurrently with
  a manual run against the real dev DB. Replaced with newest-conversation
  lookup (happy path) and distinctive-per-test-question absence checks
  (failure path) before any test code was written, so the test-writer
  subagent built the concurrency-safe version from the start.
- Rejected the stale "will fail honestly, no implementation exists" closing
  docstring in the test-writer's output at pre-gate — fixed before this
  gate, per Check 4 above.

## Verdict
**accept** — all five checks green.
