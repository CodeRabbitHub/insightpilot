# Brief — FastAPI /api/ask endpoint

Date: 2026-08-04
Milestone: M4 API (first slice — endpoint only, no streaming/persistence/auth)

Goal:
Make the existing `app.pipeline.answer.get_answer(question)` pipeline
reachable over HTTP via one new FastAPI endpoint, `POST /api/ask`.

Constraints:
- Python 3.12 + FastAPI + uvicorn (ARCHITECT.md's already-decided backend
  stack) — pin exact versions in `requirements.txt` (`fastapi==0.141.1`,
  `uvicorn[standard]==0.52.1`, confirmed current on PyPI today).
- Call `get_answer(question)` unchanged — no edits to
  `app/pipeline/{answer,generate_sql,validate_sql,execute_sql,repair_sql}.py`.
  This slice is transport only.
- Generated SQL keeps executing exclusively through `execute_sql()`'s
  existing read-only asyncpg pool (already true via `get_answer()`) — the
  API layer opens no new DB connection path for generated SQL.
- Request/response bodies are Pydantic models (ARCHITECT.md's Pydantic
  convention), even though this endpoint's response isn't LLM JSON.
- `/api/ask` is a temporary placeholder, not PRD §8's final
  `/api/conversations/{id}/messages` shape (needs F7 conversation
  persistence, out of scope) — name it clearly as interim in code/docs.
- No new dependency beyond `fastapi`/`uvicorn` without asking first.
- Tests make real calls through the real pipeline (no mocking the
  LLM/DB) — matches `test_answer_repair.py`'s existing convention, using
  FastAPI's `TestClient`.
- On repair-loop failure (both attempts fail), return a real HTTP error
  status (502, since the failure is upstream: bad generated SQL or DB),
  not an uncaught 500 crash.

Inputs:
- `app/pipeline/answer.py` — `get_answer(question)`, returns `(sql, rows)`.
- ARCHITECT.md — FastAPI decision, two-pool DB design, Pydantic-for-JSON
  convention, SSE-not-WebSockets (streaming itself out of scope, but
  don't pick a response shape that fights it later — plain JSON object
  is fine, a shape SSE would replace wholesale, not extend).
- PRD.md §8 — eventual API surface, reference only.
- `requirements.txt` — current dependency list.

Outputs:
- New `app/main.py` (single file — one endpoint doesn't earn an `app/api/`
  package yet) with a FastAPI app instance and `POST /api/ask`:
  request `{"question": str}` → `200 {"sql": str, "rows": [...]}` on
  success, `502 {"detail": str}` if `get_answer()`'s repair loop also
  fails.
- `requirements.txt` gains pinned `fastapi==0.141.1`, `uvicorn[standard]==0.52.1`.
- CLAUDE.md's Commands section gains the dev-server run line:
  `uvicorn app.main:app --reload`.
- `tests/test_api_ask.py`: happy-path (real question, real 200 response
  with non-empty rows) and failure-path (hand-crafted unrecoverable
  input that fails both repair attempts, asserting 502 not a crash),
  using FastAPI's `TestClient` against the real pipeline.

Done-check:
Both, pasted, fresh, in one sitting:
1. `python -m unittest discover -s tests -p "test_api_ask.py" -v` passes.
2. Real shipping proof: start `uvicorn app.main:app --reload`, then
   `curl -X POST localhost:8000/api/ask -H "Content-Type: application/json"
   -d '{"question": "What are the top 5 product categories by number of
   orders?"}'` — showing a real HTTP response with real SQL + rows,
   pasted verbatim.

Out-of-scope:
- SSE/streaming responses (separate M4 slice).
- Conversation/message persistence, the `app` schema's SQLAlchemy pool,
  Alembic migrations (F7 — separate slice).
- Auth (F8).
- Chart-spec and explanation generation (not yet built anywhere in the
  pipeline).
- Dashboard/cards, catalog-browser, admin/stats endpoints (PRD §8's
  other routes).
- Any change to `app/pipeline/*` itself.
- Lint/type tooling, the concurrency-safety pattern's generalization,
  `test_seed_idempotency.py`'s deadlock (all carried over, untouched).
