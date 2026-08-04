# Brief — FastAPI /api/ask/stream SSE endpoint

Date: 2026-08-04
Milestone: M4 API (second slice — SSE transport only, no per-stage progress yet)

Goal:
Add a second endpoint, `POST /api/ask/stream`, that runs the same
`get_answer(question)` call and delivers its single eventual outcome as a
Server-Sent Events response, proving the SSE transport pattern end-to-end
(ARCHITECT.md: "SSE, not WebSockets, for streaming").

Constraints:
- Python 3.12 + FastAPI/uvicorn (already added, unchanged). No new
  dependency — hand-roll SSE via Starlette's `StreamingResponse` with
  `media_type="text/event-stream"` and manually formatted `event: ...\n
  data: ...\n\n` chunks; do not add `sse-starlette` or similar without
  asking first.
- `get_answer()` and every `app/pipeline/*` file stay unchanged — still
  transport only. `get_answer()` is a single opaque awaitable with no
  intermediate progress hooks, so this slice does NOT add real per-stage
  progress events — it streams exactly one `result` event on success or
  one `error` event on failure, not a JSON blob.
- `POST /api/ask` (existing endpoint) keeps its current contract and
  passing tests completely unmodified — this is an additive new route.
- Tests make real calls through the real pipeline for the happy path (no
  mocking the LLM/DB). The failure-path test reuses this project's
  existing precedent: patch `app.main.get_answer` to raise (mirroring
  `test_api_ask.py`'s mocked-seam class), since forcing a real double-LLM
  repair failure isn't reliably reproducible through the NL-question-only
  HTTP interface.
- FastAPI's `TestClient` can consume a streamed response via
  `client.stream("POST", ...)` — use that to read and parse the SSE body.

Inputs:
- `app/main.py` — existing `/api/ask` endpoint, `AskRequest`/
  `AskResponse` models, `get_answer` import, to extend alongside.
- ARCHITECT.md — the SSE-not-WebSockets decision.
- `tests/test_api_ask.py` — test conventions to mirror (happy-path
  through the real pipeline, mocked-seam failure-path).

Outputs:
- `app/main.py` gains `POST /api/ask/stream`: same `AskRequest` body;
  `text/event-stream` response with one `result` SSE event (JSON
  `{"sql": str, "rows": [...]}`) on success, or one `error` SSE event
  (JSON `{"detail": str}`) on any `get_answer()` failure.
- `CLAUDE.md`'s Commands section notes the new route alongside the
  existing dev-server line.
- `tests/test_api_ask_stream.py`: a happy-path test (real question, real
  pipeline, parses the SSE body, asserts a `result` event with
  non-empty `sql`/`rows`) and a failure-path test (patched `get_answer`,
  asserts an `error` event, not a crash or a hung/malformed stream).

Done-check:
Both, pasted, fresh, in one sitting:
1. `python -m unittest discover -s tests -p "test_api_ask_stream.py" -v`
   passes.
2. Real shipping proof: start `uvicorn app.main:app --reload`, then
   `curl -N -X POST localhost:8000/api/ask/stream -H "Content-Type:
   application/json" -d '{"question": "What are the top 5 product
   categories by number of orders?"}'` — showing the real raw SSE
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
