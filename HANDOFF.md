# Handoff

Date: 2026-08-04
Slice just completed: plans/briefs/2026-08-03-concurrency-safety.md +
  plans/logs/2026-08-03-concurrency-safety.md (commit 534ed01)

## State of the work
- **The Stop-hook/shared-DB-row concurrency hazard (recurred 3 consecutive
  sessions per prior handoffs) is fixed.** `tests/test_verify_describe_script.py`'s
  `VerifyDescribeDoneCheckTests` and `tests/test_glossary_verify_embed.py`'s
  `GlossaryVerifyEmbedDoneCheckTests` each take a session-scoped Postgres
  advisory lock (`pg_advisory_lock(hashtext(key))`, via new
  `tests/_pg_helpers.py` functions `acquire_advisory_lock()` /
  `release_advisory_lock()`) in `setUpClass`, before touching any shared
  row — including their own `run_sync()`/`run_describe()`/
  `run_glossary_embed()` setup calls, which would otherwise silently
  "heal" a NULL/missing row a concurrent process just wrote, undoing its
  in-progress mutation. The lock is released via `cls.addClassCleanup(...)`,
  not `tearDownClass` — unittest skips `tearDownClass` entirely if
  `setUpClass` raises (a real, reachable path: both setup calls carry real
  subprocess timeouts), which would otherwise leak the session-scoped lock
  for the rest of that process's life. Both of these were genuine bugs
  found by iterating past the first design that already passed its own
  proof and review — see plans/logs/2026-08-03-concurrency-safety.md's
  "rejected or changed" for the full sequence.
- **New `tests/verify_concurrency_safety.py`** launches real concurrent
  subprocess invocations (`python -m unittest discover -s tests -p <file>
  -v`, 2 per racy file) and asserts every one exits 0 — proof under actual
  concurrent load, not "no flake observed this run." Run it via
  `python -m tests.verify_concurrency_safety` (this script has no bare
  sibling import of its own, so it's unaffected by `tests/` having no
  `__init__.py`; that only matters for the test files' own bare
  `from _pg_helpers import ...`, resolved per-subprocess via `unittest
  discover`'s sys.path insertion).
- No test method body changed in either racy test file — only
  `setUpClass`/`tearDownClass`. No prompt, model, or pipeline behavior
  touched this slice.
- M3 (retrieval + repair + evals) remains fully closed (prior slice). This
  slice was pure test-infrastructure hardening, not new product behavior.

## Proof
```
$ python -m tests.verify_concurrency_safety
  [OK] test_verify_describe_script.py (run 0): exit=0
  [OK] test_verify_describe_script.py (run 1): exit=0
  [OK] test_glossary_verify_embed.py (run 0): exit=0
  [OK] test_glossary_verify_embed.py (run 1): exit=0

verify_concurrency_safety: PASSED

$ python -m unittest discover tests
Ran 190 tests in 221.133s

OK
```
Both re-run 3+ times across the session's design iterations (initial
design → class-level redesign → lock-ordering fix → addClassCleanup fix),
always consistent on the final committed state (`534ed01`). Full detail:
`artifacts/reviews/2026-08-03-concurrency-safety.md`.

## Open questions / known issues
- **The fix is scoped to exactly these two test classes, not enforced
  generically.** A future test added with the same "real, committed
  mutation of a shared row + subprocess check + restore" shape would need
  the same `acquire_advisory_lock`/`addClassCleanup` pattern applied by
  hand — nothing catches a new racy test automatically. Not urgent (no
  such test is planned), but worth remembering if one shows up.
- `tests/test_seed_idempotency.py`'s own real Postgres deadlock (M1-era,
  unrelated code, first surfaced as supporting evidence of concurrent
  overlap in the repair-loop slice) was never itself investigated or
  fixed — still out of scope, still untouched.
- **FastAPI and uvicorn are not yet in `requirements.txt`.** ARCHITECT.md
  already commits to Python 3.12 + FastAPI as the backend framework, and
  PRD.md section 8 lays out the eventual API surface, but no code under
  `app/` uses either yet — the next slice is the first to add them.
- The doubled-Voyage-call-per-question design cost
  (`app/pipeline/generate_sql.py`) remains unoptimized — accepted,
  documented in code, not a blocker.
- Lint/type tooling (`ruff`, `mypy`) and the test runner (`unittest`, not
  `pytest`) remain unaddressed, carried over from every prior slice —
  still not blocking.

## Next slice (the brief, written NOW while context is hot)
Goal:
Make the existing `app.pipeline.answer.get_answer(question)` pipeline
reachable over HTTP via a single new FastAPI endpoint — the smallest
useful cut of M4, proving the pipeline works behind a real ASGI server
before adding SSE streaming or conversation/message persistence on top.

Constraints:
- Python 3.12 + FastAPI + uvicorn (ARCHITECT.md's already-decided backend
  stack) — first slice to actually add them; pin exact versions in
  `requirements.txt` (currently missing both).
- Call the existing `get_answer(question)` from `app/pipeline/answer.py`
  unchanged — no modification to the pipeline, retrieval, generation,
  validation, execution, or repair logic. This slice is transport only.
- Generated SQL must keep executing exclusively through the existing
  read-only asyncpg pool inside `execute_sql()` (already true via
  `get_answer()`) — the API layer must not open any new DB connection
  path for generated SQL, never raw, never through an app-side pool.
- Request/response bodies are Pydantic models (ARCHITECT.md's existing
  Pydantic convention), even though this endpoint's response isn't LLM
  JSON — keep FastAPI's own typed-model idiom, not raw dicts.
- The endpoint path is a temporary placeholder (e.g. `POST /api/ask`), not
  PRD.md section 8's final `/api/conversations/{id}/messages` shape —
  that requires conversation persistence (F7), explicitly out of scope
  here. Name it clearly as interim in code/docs so it isn't mistaken for
  the final API surface.
- No new dependency beyond `fastapi`/`uvicorn` (already ARCHITECT.md-
  mandated, not drift) without asking first.
- Tests make real calls through the real pipeline (no mocking the
  LLM/DB), matching this project's existing no-mock convention — mirrors
  how `app/pipeline/verify_answer.py` already proves `get_answer()`.

Inputs:
- `app/pipeline/answer.py` — `get_answer(question)`, returns `(sql,
  rows)`, the exact function to wrap.
- ARCHITECT.md — Python 3.12 + FastAPI decision, two-pool DB design,
  Pydantic-for-JSON convention, SSE-not-WebSockets decision (streaming
  itself is out of scope this slice, but don't pick a response shape that
  fights it later).
- PRD.md section 8 (API Surface) — for eventual shape reference only, not
  literally implemented this slice.
- `requirements.txt` — current dependency list, to extend.

Outputs:
- New `app/api/` package (or `app/main.py`, exact layout confirmed at Gate
  1) with a FastAPI app instance and one `POST /api/ask` endpoint:
  request `{"question": str}` → response `{"sql": str, "rows": [...]}` on
  success; a real HTTP error status (not an uncaught crash) if
  `get_answer()`'s repair loop also fails.
- `requirements.txt` gains pinned `fastapi`/`uvicorn` entries.
- A documented way to run the dev server (e.g. `uvicorn app.main:app
  --reload`), added to CLAUDE.md's Commands section.
- A test proving the endpoint works end-to-end against the real pipeline
  (FastAPI `TestClient` or a real running server — confirmed at Gate 1),
  plus a happy-path and a failure-path (both attempts fail) case.

Done-check:
Both, pasted, fresh, in one sitting: (1) the new endpoint test file run
standalone, e.g. `python -m unittest discover -s tests -p
"test_api_ask.py" -v`, passing; (2) real shipping proof — start `uvicorn
app.main:app` and `curl -X POST localhost:8000/api/ask -d
'{"question": "..."}'` (exact question/flags confirmed at Gate 1),
showing a real HTTP response with real SQL + rows, pasted verbatim.

Out-of-scope:
- SSE/streaming responses (separate M4 slice).
- Conversation/message persistence, the `app` schema's SQLAlchemy pool,
  Alembic migrations (F7 — separate slice).
- Auth (F8).
- Chart-spec and explanation generation (not yet built anywhere in the
  pipeline — separate slice(s) before or alongside the real chat UI).
- Dashboard/cards endpoints, catalog-browser endpoint, admin/stats
  endpoint (PRD section 8's other routes).
- Any change to `app/pipeline/*` itself.
- Lint/type tooling, the concurrency-safety pattern's generalization to
  future tests, `test_seed_idempotency.py`'s deadlock.
