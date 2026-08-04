# Review gate — FastAPI /api/ask endpoint

Date: 2026-08-04
Brief: plans/briefs/2026-08-04-fastapi-ask-endpoint.md
Diff reviewed: working tree — `app/main.py` (new), `tests/test_api_ask.py`
(new), `requirements.txt` (+2 lines), `CLAUDE.md` (+3 lines),
`tests/test_llm_description_setup.py` (+6 lines, see Check 3),
`plans/briefs/2026-08-04-fastapi-ask-endpoint.md` (new, the brief itself).
`plans/logs/_auto-capture.md`'s 103-line diff is the hook-appended commit
log, mechanical, not authored this slice.

## 1. The diff is small enough to review
```
CLAUDE.md                   |   3 ++
plans/logs/_auto-capture.md | 103 ++++ (hook-generated, not reviewed content)
requirements.txt            |   2 ++
```
Plus new files: `app/main.py` (32 lines), `tests/test_api_ask.py` (236
lines, mostly docstring + two small test classes), the brief (76 lines,
docs). All human-readable in full. **PASS.**

## 2. The stated goal matches the actual change
Goal: make `get_answer(question)` reachable over HTTP via one `POST
/api/ask` endpoint. The diff adds exactly that — `app/main.py` with one
FastAPI app, one route, Pydantic request/response models, a try/except
mapping any pipeline failure to 502 — and nothing else. No pipeline file
touched. No extra routes, no `app/api/` package (single file, per the
brief's Outputs), no auth/persistence/streaming added. **PASS.**

## 3. The eval or test passed
Fresh, this session, after the no-slop fixes below:
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
No prompt/model/pipeline behavior changed this slice, so `evals/run.py`
was not re-run (not required by CLAUDE.md's rule, which triggers on
prompt/pipeline changes only). **PASS.**

The Stop hook (`stop_verify`, which runs the *full* suite on every
"done" claim, capped at 3 attempts) caught a real failure on attempt 1:
`tests/test_llm_description_setup.py::RequirementsTests::
test_requirements_gains_no_other_new_dependencies` — a pre-existing
guard test (from the 2026-08-02 llm-table-descriptions slice) that
maintains a running ledger of every pre-approved `requirements.txt`
dependency, extended once per slice that legitimately adds one (each
entry citing its approving brief: `sqlglot`, `asyncpg`, `voyageai`,
`pyyaml`). Adding `fastapi`/`uvicorn` without extending that ledger
correctly failed it. Fixed by extending `NEWLY_APPROVED_PACKAGES` with
`{"fastapi", "uvicorn"}`, following the exact same comment convention,
citing this slice's brief — not by weakening or deleting the test itself
(CLAUDE.md's standing rule). Re-ran the *full* suite fresh after the fix:
```
$ .venv/Scripts/python.exe -m unittest discover tests
Ran 197 tests in 236.355s

OK
```
197 = the prior 190 + this slice's 7 new `test_api_ask.py` tests, all
passing. **PASS.**

## 4. The no-slop review found no unresolved issues
`no-slop-reviewer` subagent findings and resolutions:

1. **Fabricated citation** (`tests/test_api_ask.py`) — the failure-path
   test's docstring claimed its mock-based design was "per the brief's
   own suggestion," quoting text that does not appear in the brief. The
   suggestion was actually mine, given to the test-writer subagent in its
   prompt, not the brief's. **Fixed**: docstring now correctly attributes
   this as a deliberate, Gate-1-approved deviation from the brief's
   literal "hand-crafted unrecoverable input" wording, with the real
   reason (no seam to force a real double-LLM failure over the
   NL-question-only HTTP interface, unlike `test_answer_repair.py`'s
   direct `BROKEN_SQL` injection).
2. **Untested edge / inaccurate comment** (`app/main.py`) — the reviewer
   ran a live empty-question request and got a real 502 from a Voyage
   embedding-input error, not a "repair-loop failure" as the code
   comment specifically claimed. **Fixed**: comment reworded to the
   accurate, general claim (any pipeline failure -> 502); *also* added
   `AskEndpointRealFailureInputTests.
   test_empty_question_maps_to_502_via_the_real_pipeline` — a real,
   unmocked, deterministic failure case (empty question rejected by
   Voyage before the repair loop even runs), closing the coverage gap
   the mocked test alone left open. This is arguably a truer fulfillment
   of the brief's "hand-crafted unrecoverable input" language than what
   was originally written.
3. **Minor duplication** (`tests/test_api_ask.py`) — the fake failing
   `get_answer` was defined identically twice. **Fixed**: extracted to
   one module-level `_fake_get_answer_that_fails`.

All three resolved and re-verified (test run above is post-fix). No
open findings. **PASS.**

## 5. The shipping proof is attached
Real server, real question, run fresh at gate time:
```
$ .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
$ curl -s -X POST http://127.0.0.1:8000/api/ask -H "Content-Type: application/json" \
    -d '{"question": "What are the top 5 product categories by number of orders?"}' \
    -w "\nHTTP_STATUS:%{http_code}\n"
{"sql":"SELECT p.product_category_name, COUNT(DISTINCT oi.order_id) AS order_count FROM olist.order_items oi JOIN olist.products p ON oi.product_id = p.product_id GROUP BY p.product_category_name ORDER BY order_count DESC LIMIT 5","rows":[{"product_category_name":"cama_mesa_banho","order_count":9417},{"product_category_name":"beleza_saude","order_count":8836},{"product_category_name":"esporte_lazer","order_count":7720},{"product_category_name":"informatica_acessorios","order_count":6689},{"product_category_name":"moveis_decoracao","order_count":6449}]}
HTTP_STATUS:200
```
`cama_mesa_banho: 9417` matches `evals/questions.yaml`'s hand-verified
expected value exactly, confirming the endpoint is running the real,
correct pipeline, not a stub. **PASS.**

## Rejected or changed
Rejected the test-writer's original failure-path design as-delivered:
its docstring misattributed a design choice to the brief (fabricated
citation) and left the brief's actual "hand-crafted unrecoverable input"
requirement unimplemented in substance (a pure mock, no real failure
exercised). Required a real, unmocked failure test added
(`test_empty_question_maps_to_502_via_the_real_pipeline`) plus corrected
docstrings/comments in both the test file and `app/main.py`, not just
accepted as delivered.

## Verdict
**accept** — all five checks green after the no-slop fixes above.
