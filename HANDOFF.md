# Handoff

Date: 2026-08-04
Slice just completed: plans/briefs/2026-08-04-fastapi-ask-endpoint.md +
  plans/logs/2026-08-04-fastapi-ask-endpoint.md (commits f5f35a2, fb52aac)

## State of the work
- **M4's first slice is done: `get_answer(question)` is reachable over
  HTTP.** New `app/main.py` — a FastAPI app with one `POST /api/ask`
  endpoint — wraps the existing, unchanged `app.pipeline.answer
  .get_answer(question)`: request `{"question": str}` -> `200
  {"sql": str, "rows": [...]}` on success, `502 {"detail": str}` on any
  pipeline failure (SQL generation, validation, execution, or the one
  repair attempt).
- `requirements.txt` gained pinned `fastapi==0.141.1`,
  `uvicorn[standard]==0.52.1` — both actually installed into `.venv` and
  proven working, not just pinned on paper. `tests/test_llm_description
  _setup.py`'s dependency ledger (`NEWLY_APPROVED_PACKAGES`, extended
  once per slice since 2026-08-02) was extended to match, per its own
  established convention.
- `CLAUDE.md`'s Commands section documents `uvicorn app.main:app
  --reload` as the interim dev-server command.
- **`tests/test_api_ask.py` (7 tests, all real, no mocking of the
  LLM/DB except one deliberate seam):** a happy-path class hitting the
  real pipeline via FastAPI's `TestClient`; a mocked-seam class proving
  the exception->502 transport contract deterministically (patches
  `app.main.get_answer`, mirroring `test_answer_repair.py`'s
  `RetryOnceTests` precedent, since a real double-LLM-repair-failure
  can't be forced deterministically through the NL-question-only HTTP
  interface); and a genuinely real, unmocked failure case — an empty
  question is rejected by Voyage's embedding call before the repair loop
  even runs, proving a real "hand-crafted unrecoverable input" case end
  to end.
- No `app/pipeline/*` file was touched. Full suite: 197/197 passing
  (190 prior + this slice's 7).

## Proof
```
$ .venv/Scripts/python.exe -m unittest discover -s tests -p "test_api_ask.py" -v
test_502_response_body_has_a_detail_string ... ok
test_pipeline_exception_maps_to_a_502_not_a_crash ... ok
test_response_body_has_exactly_the_sql_and_rows_keys ... ok
test_response_rows_is_a_non_empty_list ... ok
test_response_sql_is_a_non_empty_string ... ok
test_returns_200_for_the_fixed_question ... ok
test_empty_question_maps_to_502_via_the_real_pipeline ... ok

Ran 7 tests in 7.207s

OK
```
```
$ .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
$ curl -s -X POST http://127.0.0.1:8000/api/ask -H "Content-Type: application/json" \
    -d '{"question": "What are the top 5 product categories by number of orders?"}' \
    -w "\nHTTP_STATUS:%{http_code}\n"
{"sql":"SELECT p.product_category_name, COUNT(DISTINCT oi.order_id) AS order_count FROM olist.order_items oi JOIN olist.products p ON oi.product_id = p.product_id GROUP BY p.product_category_name ORDER BY order_count DESC LIMIT 5","rows":[{"product_category_name":"cama_mesa_banho","order_count":9417}, ...]}
HTTP_STATUS:200
```
`cama_mesa_banho: 9417` matches `evals/questions.yaml`'s hand-verified
value exactly. Full suite: `Ran 197 tests in 236.355s / OK`. Full detail:
`artifacts/reviews/2026-08-04-fastapi-ask-endpoint.md`.

## Open questions / known issues
- **Decimal-valued rows serialize as JSON strings, not numbers** —
  verified this session: `curl .../api/ask -d '{"question": "What is
  the average order value?"}'` returned
  `{"average_order_value":"137.7540763788944520"}` (a string), via
  FastAPI's default `jsonable_encoder` behavior for `Decimal` inside
  `dict[str, Any]`. Not a bug, but the eventual chart-rendering/frontend
  work needs to know to parse numeric-looking strings, not assume
  native JSON numbers.
- **`plans/logs/_auto-capture.md` has been silently uncommitted across
  at least the last 3 commits** (`534ed01`, `305283f`, `8cbc8e6`, and
  now this slice's `f5f35a2`/`fb52aac` too) — the `capture_commit` hook
  appends to it after every commit, but no commit in this observed
  history has ever included that file itself, so it just accumulates as
  a permanently-modified tracked file. Pre-existing, not caused by this
  slice, not fixed this slice (out of scope) — flagging since it looks
  like a workflow gap worth a deliberate decision (commit it every time?
  gitignore it? something else?), not more silent accumulation.
- Starlette's `TestClient` (used by `tests/test_api_ask.py`) emits
  `StarletteDeprecationWarning: Using httpx with starlette.testclient is
  deprecated; install httpx2 instead` — harmless today, not acted on
  since adding `httpx2` would be a new dependency without asking first.
- `tests/test_seed_idempotency.py`'s own real Postgres deadlock (M1-era,
  unrelated code) remains uninvestigated.
- The doubled-Voyage-call-per-question design cost
  (`app/pipeline/generate_sql.py`) remains unoptimized — accepted,
  documented in code.
- Lint/type tooling (`ruff`, `mypy`) and the test runner (`unittest`,
  not `pytest`) remain unaddressed, carried over from every prior slice.
- The concurrency-safety pattern (session-scoped advisory locks) is
  still scoped to exactly the two test classes it was applied to, not
  generalized — unchanged from the prior handoff.

## Next slice (the brief, written NOW while context is hot)
Goal:
Add a second, SSE-streaming endpoint, `POST /api/ask/stream`, that runs
the same `get_answer(question)` call and delivers its outcome as a
Server-Sent Events response — proving the SSE transport pattern
end-to-end (ARCHITECT.md's SSE-not-WebSockets decision) before later
work adds real incremental per-stage or per-token content once
chart-spec/explanation generation exists to stream.

Constraints:
- Python 3.12 + FastAPI/uvicorn (already added). No new dependency —
  hand-roll SSE via Starlette's `StreamingResponse` with
  `media_type="text/event-stream"` and manually formatted `event: ...\n
  data: ...\n\n` chunks; do not add `sse-starlette` or similar without
  asking first. ARCHITECT.md's own reasoning ("one-way token streams
  need nothing more" than SSE) implies a dedicated library isn't needed
  for this either.
- `get_answer()` and every other `app/pipeline/*` file stay unchanged —
  still transport only. `get_answer()` is a single opaque awaitable with
  no intermediate progress hooks, so this slice does NOT add real
  per-stage progress events (that needs pipeline instrumentation, a
  separate future decision) — it streams the single eventual outcome
  (one `result` event on success, one `error` event on failure) over
  SSE, not a JSON blob.
- `POST /api/ask` (this slice's just-shipped endpoint) must keep its
  existing contract and passing tests completely unmodified — this is
  an additive new route, not a change to `/api/ask`.
- Tests make real calls through the real pipeline for the happy path (no
  mocking the LLM/DB), matching this project's convention; the
  failure-path test may reuse the prior slice's approach (patching
  `app.main.get_answer`, or the real empty-question case) — confirm
  which at Gate 1.
- FastAPI `TestClient` can consume a streamed response via
  `client.stream("POST", ...)` — use that (or raw `httpx`, already
  installed) to read and parse the SSE body in tests.

Inputs:
- `app/main.py` — existing `/api/ask` endpoint, `AskRequest`/
  `AskResponse` models, `get_answer` import, to extend alongside (not
  replace).
- ARCHITECT.md — the SSE-not-WebSockets decision and its reasoning.
- `tests/test_api_ask.py` — this slice's test conventions to mirror.

Outputs:
- `app/main.py` gains `POST /api/ask/stream`: same `AskRequest` body;
  `text/event-stream` response with one `result` SSE event (JSON
  `{"sql": str, "rows": [...]}`) on success, or one `error` SSE event
  (JSON `{"detail": str}`) on any `get_answer()` failure.
- `CLAUDE.md` notes the new route alongside the existing dev-server line.
- `tests/test_api_ask_stream.py`: a happy-path test (real question, real
  pipeline, parses the SSE body, asserts a `result` event with
  non-empty `sql`/`rows`) and a failure-path test (asserts an `error`
  event, not a crash or a hung/malformed stream).

Done-check:
Both, pasted, fresh, in one sitting: (1)
`python -m unittest discover -s tests -p "test_api_ask_stream.py" -v`
passing; (2) real shipping proof — start `uvicorn app.main:app --reload`
and `curl -N -X POST localhost:8000/api/ask/stream -d '{"question":
"..."}'` (exact question confirmed at Gate 1), showing the real raw SSE
`event:`/`data:` lines, pasted verbatim.

Out-of-scope:
- Real incremental per-stage or per-token streaming (requires
  instrumenting `app/pipeline/*` itself — separate future slice, only
  worth doing once there's real generated text, e.g. an explanation
  step, to stream).
- Conversation/message persistence, the `app` schema's SQLAlchemy pool,
  Alembic migrations (F7 — separate slice).
- Auth (F8).
- Chart-spec and explanation generation (not yet built anywhere in the
  pipeline).
- Any change to `/api/ask`'s existing behavior, or to `app/pipeline/*`.
- Lint/type tooling, `_auto-capture.md`'s uncommitted-backlog question,
  `test_seed_idempotency.py`'s deadlock (all carried over, untouched).
