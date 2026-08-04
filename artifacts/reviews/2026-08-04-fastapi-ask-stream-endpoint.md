# Review gate — FastAPI /api/ask/stream SSE endpoint

Date: 2026-08-04
Brief: plans/briefs/2026-08-04-fastapi-ask-stream-endpoint.md
Diff reviewed: working tree (uncommitted) —
  modified `app/main.py`, `CLAUDE.md`;
  new `tests/test_api_ask_stream.py`, `plans/briefs/2026-08-04-fastapi-ask-stream-endpoint.md`.
  (`plans/logs/_auto-capture.md`'s diff is the pre-existing, unrelated
  auto-capture hook backlog — carried over, not part of this slice.)

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review
`git diff --stat`:
```
 CLAUDE.md                   |   6 +-
 app/main.py                 |  34 ++++++++++
 plans/logs/_auto-capture.md | 161 ++++++++++++++++++++++++++++++++++++++++++++
 3 files changed, 199 insertions(+), 2 deletions(-)
```
plus 2 new files (`tests/test_api_ask_stream.py`, the brief). `app/main.py`'s
34 added lines and `CLAUDE.md`'s 4-line doc change were read in full,
line by line. PASS.

## 2. The stated goal matches the actual change
Brief's Goal: add `POST /api/ask/stream`, running the same
`get_answer(question)` call, delivering its outcome as one SSE
`result`/`error` event — proving the SSE transport (ARCHITECT.md).

The diff does exactly that: `app/main.py` gains `_ask_stream_events`
(one `await get_answer()`, one formatted SSE chunk on success or
failure) and the `POST /api/ask/stream` route wrapping it in a
`StreamingResponse`. `/api/ask`'s existing `ask()` function is
byte-for-byte unmodified. `CLAUDE.md` gets the one doc line the brief's
Outputs calls for. No extra behavior, no scope creep — the one
mid-review addition (routing the success payload through the existing
`AskResponse` model instead of a raw dict, see Check 4) is a
consistency fix within the same route, not new scope. PASS.

## 3. The eval or test passed
No prompt or pipeline file changed, so no eval run is required.
Done-check, run fresh:
```
$ .venv/Scripts/python.exe -m unittest discover -s tests -p "test_api_ask_stream.py" -v
test_body_contains_exactly_one_error_event ... ok
test_body_contains_no_result_event ... ok
test_error_event_data_has_a_non_empty_detail_string ... ok
test_pipeline_exception_is_not_a_crash_or_hung_stream ... ok
test_pipeline_exception_still_returns_200_not_an_http_error ... ok
test_body_contains_exactly_one_result_event ... ok
test_body_contains_no_error_event ... ok
test_result_event_data_has_exactly_the_sql_and_rows_keys ... ok
test_result_event_rows_is_a_non_empty_list ... ok
test_result_event_sql_is_a_non_empty_string ... ok
test_returns_200_for_the_fixed_question ... ok

Ran 11 tests in 8.162s

OK
```
Full suite (proves `/api/ask` and everything else stayed green):
```
$ .venv/Scripts/python.exe -m unittest discover tests
...............................................................................................
.................................................................................................................
Ran 208 tests in 260.384s

OK
```
(197 prior + 11 new = 208.) PASS.

## 4. The no-slop review found no unresolved issues
First pass (`no-slop-reviewer` subagent) flagged one finding: the SSE
success path built `{"sql","rows"}` as a raw dict serialized via
`jsonable_encoder`, instead of reusing the `AskResponse` model
`/api/ask` already validates through — so `/api/ask/stream` streamed
`get_answer()`'s output with no shape validation, an unflagged
divergence between the two "same contract" endpoints.

Resolved: `_ask_stream_events` now constructs `AskResponse(sql=sql,
rows=rows)` and serializes that (with a comment naming why), so both
endpoints validate identically. A follow-up `no-slop-reviewer` pass on
the fixed diff confirmed the finding is genuinely resolved and found no
other issues across all 10 checklist categories (dead code, error
handling, duplication, naming, untested edges, comments, consistency,
scope, fake-done, verified-not-claimed). PASS.

## 5. The shipping proof is attached
Live server (`uvicorn app.main:app`), real curl calls against the
running endpoint — not just the test suite:

Success case:
```
$ curl -N -X POST localhost:8000/api/ask/stream -H "Content-Type: application/json" \
    -d '{"question": "What are the top 5 product categories by number of orders?"}'
event: result
data: {"sql": "SELECT p.product_category_name, COUNT(DISTINCT oi.order_id) AS order_count FROM olist.order_items oi JOIN olist.products p ON oi.product_id = p.product_id GROUP BY p.product_category_name ORDER BY order_count DESC LIMIT 5", "rows": [{"product_category_name": "cama_mesa_banho", "order_count": 9417}, {"product_category_name": "beleza_saude", "order_count": 8836}, {"product_category_name": "esporte_lazer", "order_count": 7720}, {"product_category_name": "informatica_acessorios", "order_count": 6689}, {"product_category_name": "moveis_decoracao", "order_count": 6449}]}
HTTP_STATUS:200
```
(`cama_mesa_banho: 9417` matches the hand-verified value from the
prior `/api/ask` slice's own shipping proof.)

Failure case (empty question — same real, deterministic failure case
used in the prior slice, rejected by Voyage's embedding call):
```
$ curl -N -X POST localhost:8000/api/ask/stream -H "Content-Type: application/json" -d '{"question": ""}'
event: error
data: {"detail": "The request body is not valid JSON, or some arguments were not specified properly. In particular, Error for argument 'input': Value error, Input cannot contain empty strings or empty lists"}
HTTP_STATUS:200
```
Confirms the brief's key contract live: HTTP status is always 200; the
outcome is signaled by the SSE event type. PASS.

## Rejected or changed
- Changed: the success-path payload was rewritten mid-review to route
  through `AskResponse` instead of a raw dict (Check 4 finding), so
  `/api/ask` and `/api/ask/stream` validate `get_answer()`'s output the
  same way. This is the only change made during the gate.

## Verdict
accept — all five checks green.
