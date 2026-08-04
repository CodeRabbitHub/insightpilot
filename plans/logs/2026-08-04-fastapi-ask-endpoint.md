# Slice log — FastAPI /api/ask endpoint

Date: 2026-08-04
Brief: plans/briefs/2026-08-04-fastapi-ask-endpoint.md

## The plan you approved
Single new `app/main.py` (not an `app/api/` package yet) with one FastAPI
app and `POST /api/ask`, wrapping `get_answer(question)` unchanged behind
Pydantic request/response models; any pipeline exception maps to 502. The
happy-path test hits the real pipeline (real LLM + DB) via `TestClient`;
the failure-path test patches the one seam `app/main.py` calls
(`app.main.get_answer`) rather than relying on a real, nondeterministic
double-LLM repair failure — mirroring `test_answer_repair.py`'s
`RetryOnceTests` precedent for isolating a propagation claim from real
I/O.

## The diff you accepted
Commit `f5f35a2` — "Add POST /api/ask FastAPI endpoint wrapping
get_answer()". 7 files changed, 484 insertions(+):
`app/main.py` (new), `tests/test_api_ask.py` (new, 7 tests),
`requirements.txt` (+fastapi/uvicorn pins), `CLAUDE.md` (+dev command),
`tests/test_llm_description_setup.py` (+dependency-ledger entries),
`plans/briefs/` + `artifacts/reviews/` for this slice. Full gate record:
`artifacts/reviews/2026-08-04-fastapi-ask-endpoint.md`.

## The done-check output
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
{"sql":"SELECT p.product_category_name, COUNT(DISTINCT oi.order_id) AS order_count FROM olist.order_items oi JOIN olist.products p ON oi.product_id = p.product_id GROUP BY p.product_category_name ORDER BY order_count DESC LIMIT 5","rows":[{"product_category_name":"cama_mesa_banho","order_count":9417},{"product_category_name":"beleza_saude","order_count":8836},{"product_category_name":"esporte_lazer","order_count":7720},{"product_category_name":"informatica_acessorios","order_count":6689},{"product_category_name":"moveis_decoracao","order_count":6449}]}
HTTP_STATUS:200
```
Full suite fresh, post-fix: `Ran 197 tests in 236.355s / OK` (190 prior +
this slice's 7).

## One thing you rejected or changed
Two things, both caught by process, not rubber-stamped:
1. **no-slop pre-gate** rejected the test-writer's failure-path test as
   delivered: its docstring falsely attributed a mock-based design
   choice to "the brief's own suggestion" — a quote that appears nowhere
   in the brief (it was actually a suggestion I gave the test-writer
   subagent in its own prompt). Required correcting the attribution
   *and* adding a genuinely real, unmocked failure test
   (`test_empty_question_maps_to_502_via_the_real_pipeline`, an empty
   question rejected by Voyage before the repair loop runs) — a truer
   fulfillment of the brief's literal "hand-crafted unrecoverable input"
   ask than what was first written.
2. **stop_verify hook** caught a real full-suite failure on attempt 1:
   `test_llm_description_setup.py`'s dependency ledger test failed
   because `fastapi`/`uvicorn` weren't added to its
   `NEWLY_APPROVED_PACKAGES` allowlist. Fixed by extending the ledger
   (following its own established per-slice-extension pattern, citing
   this brief), not by touching the assertion.

Neither is a new pattern needing promotion: the no-slop role already
exists precisely to catch #1-type issues, and the dependency ledger's
extend-per-slice convention is already the promoted pattern for #2 — it
worked exactly as designed both times.

## The next smallest slice
Confirmed with the user: SSE-stream `/api/ask`'s response (tokens as they
generate, or at minimum staged progress events) instead of one blocking
JSON blob, since ARCHITECT.md already commits to SSE for streaming and
PLAN.md's M4 orders it right after the bare endpoint, before conversation
persistence (F7).
