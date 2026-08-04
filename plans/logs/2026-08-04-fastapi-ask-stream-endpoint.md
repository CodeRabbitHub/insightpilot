# Slice log — FastAPI /api/ask/stream SSE endpoint

Date: 2026-08-04
Brief: plans/briefs/2026-08-04-fastapi-ask-stream-endpoint.md

## The plan you approved
Add `POST /api/ask/stream` to the existing `app/main.py` (no new file).
Hand-roll SSE via `StreamingResponse` over an async generator that runs
`await get_answer(question)` once and yields exactly one formatted SSE
chunk: `event: result` with `{"sql", "rows"}` on success, `event: error`
with `{"detail"}` on failure — always HTTP 200, since once the stream
starts there's no later status code to change. `/api/ask` untouched;
`app/pipeline/*` untouched.

## The diff you accepted
Commit `96a4397` — "Add POST /api/ask/stream SSE endpoint wrapping
get_answer()". 5 files changed, 535 insertions(+): `app/main.py`
(+34 lines), `CLAUDE.md` (+doc line), `tests/test_api_ask_stream.py`
(new, 11 tests), `plans/briefs/` + `artifacts/reviews/` for this slice.
Full gate record: `artifacts/reviews/2026-08-04-fastapi-ask-stream-endpoint.md`.

## The done-check output
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
```
$ .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
$ curl -N -X POST localhost:8000/api/ask/stream -H "Content-Type: application/json" \
    -d '{"question": "What are the top 5 product categories by number of orders?"}' \
    -w "\nHTTP_STATUS:%{http_code}\n"
event: result
data: {"sql": "SELECT p.product_category_name, COUNT(DISTINCT oi.order_id) AS order_count FROM olist.order_items oi JOIN olist.products p ON oi.product_id = p.product_id GROUP BY p.product_category_name ORDER BY order_count DESC LIMIT 5", "rows": [{"product_category_name": "cama_mesa_banho", "order_count": 9417}, {"product_category_name": "beleza_saude", "order_count": 8836}, {"product_category_name": "esporte_lazer", "order_count": 7720}, {"product_category_name": "informatica_acessorios", "order_count": 6689}, {"product_category_name": "moveis_decoracao", "order_count": 6449}]}
HTTP_STATUS:200
```
`cama_mesa_banho: 9417` matches the prior slice's hand-verified value.
Also confirmed live: an empty question produces `event: error` with a
real, non-empty `detail`, still HTTP 200 (the failure-signaling
contract). Full suite fresh: `Ran 208 tests in 260.384s / OK` (197
prior + this slice's 11).

## One thing you rejected or changed
**no-slop pre-gate** caught a real design gap in the first draft: the
SSE success path built `{"sql", "rows"}` as a raw dict serialized
through `jsonable_encoder` directly, instead of reusing the
`AskResponse` model `/api/ask` already validates its own response
through. That meant `/api/ask/stream` streamed `get_answer()`'s output
completely unvalidated, while `/api/ask` got shape validation for free
via `response_model` — a real, silent divergence between two endpoints
meant to share a contract. Fixed by routing the success payload through
`AskResponse(sql=sql, rows=rows)` before encoding, so both endpoints
validate identically. Re-verified clean by a second no-slop pass.

This is a new pattern (manual/hand-rolled serialization bypassing an
existing validation model), not a repeat of anything in the prior
slice's log — no promotion action taken, but worth watching: any future
endpoint that serializes by hand (not through FastAPI's `response_model`
machinery) should route through the same Pydantic model the "normal"
endpoint uses, not rebuild the shape as a raw dict.

## The next smallest slice
Confirmed with the user: F7 conversation/message persistence — add the
`app` schema's SQLAlchemy pool, an Alembic migration, and
`conversations`/`messages` tables, so both `/api/ask` and
`/api/ask/stream` can be backed by real persisted history. This is the
one M4 milestone item every prior brief's Out-of-scope has deferred,
and it's the natural next piece now that both HTTP and SSE transport
are proven end-to-end.
