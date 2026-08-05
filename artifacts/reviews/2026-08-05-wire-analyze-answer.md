# Review gate — wire analyze_answer into get_answer()

Date: 2026-08-05
Brief: plans/briefs/2026-08-05-wire-analyze-answer.md
Diff reviewed: working tree (uncommitted) — `git diff` against HEAD (88088d3)

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review

```
$ git diff --stat
 app/main.py                           | 16 ++++---
 app/pipeline/answer.py                | 22 ++++++---
 app/pipeline/verify_analyze_answer.py |  4 +-
 app/pipeline/verify_answer.py         |  6 +--
 evals/run.py                          |  2 +-
 plans/logs/_auto-capture.md           | 24 ++++++++++
 tests/test_analyze_answer.py          | 20 +++++++-
 tests/test_api_ask.py                 | 88 ++++++++++++++++++++++++++++++++---
 tests/test_api_ask_stream.py          | 47 +++++++++++++++++--
 tests/test_api_conversations.py       | 54 +++++++++++++++++++--
 tests/test_api_conversations_read.py  | 33 +++++++++++--
 tests/test_question_parameter.py      | 36 ++++++++++++--
 12 files changed, 309 insertions(+), 43 deletions(-)
 + 2 new files: plans/briefs/2026-08-05-wire-analyze-answer.md,
   tests/test_wire_analyze_answer.py
```

Small, mechanical wiring diff. Every hunk in the 5 application files is a
direct consequence of the brief's 3-tuple/`analysis`-field contract; the
6 test-file hunks are the corresponding shape updates. Read every line.
**PASS.**

## 2. The stated goal matches the actual change

Brief's Goal: wire the already-proven `analyze_answer()` into the real
pipeline so `get_answer()` calls it internally and every endpoint's JSON
response carries real summary/explanation/chart_spec/follow_ups data.

What the diff does:
- `get_answer()` (app/pipeline/answer.py) calls `analyze_answer(question,
  sql, rows)` itself, immediately after `_answer_with_repair()` succeeds,
  and returns `(sql, rows, analysis)`. No try/except — a failure
  propagates uncaught, matching the brief's Constraint exactly.
- `AskResponse`/`ConversationMessageResult` (app/main.py) each gain a
  nested `analysis: AnalyzeResponse` field, reusing the real model
  directly. All three endpoints (`/api/ask`, `/api/ask/stream`,
  `/api/conversations/{id}/messages`) updated to unpack the 3-tuple and
  forward `analysis`. `_persist_exchange()`/`_persist_message_pair()`
  needed no code change, as predicted.
- Every existing call site/test that unpacked the old 2-tuple
  (`evals/run.py`, `verify_answer.py`, `verify_analyze_answer.py`,
  `test_question_parameter.py`, `test_analyze_answer.py`) updated to
  match.
- No change to `analyze_answer.py`, `prompts/analyze.md`,
  `ROW_SAMPLE_CAP`, the repair loop, or any frontend file — all
  confirmed out-of-scope items respected.

No missing behavior, no unrequested extras. **PASS.**

## 3. The eval or test passed

Brief's done-check, run fresh:

```
$ .venv/Scripts/python.exe -m app.pipeline.verify_answer
SQL:
SELECT p.product_category_name, COUNT(DISTINCT oi.order_id) AS order_count FROM olist.order_items oi JOIN olist.products p ON oi.product_id = p.product_id GROUP BY p.product_category_name ORDER BY order_count DESC LIMIT 5

Rows:
{'product_category_name': 'cama_mesa_banho', 'order_count': 9417}
{'product_category_name': 'beleza_saude', 'order_count': 8836}
{'product_category_name': 'esporte_lazer', 'order_count': 7720}
{'product_category_name': 'informatica_acessorios', 'order_count': 6689}
{'product_category_name': 'moveis_decoracao', 'order_count': 6449}

Summary:
The top 5 product categories by number of orders are cama_mesa_banho (9,417), beleza_saude (8,836), esporte_lazer (7,720), informatica_acessorios (6,689), and moveis_decoracao (6,449).

Explanation:
The query joined order_items with products on product_id, grouped by product_category_name, and counted distinct order_ids per category, then sorted descending and limited to 5 rows. The result shows cama_mesa_banho (bed/table/bath) as the leading category with 9,417 orders, followed closely by beleza_saude (health/beauty) and esporte_lazer (sports/leisure), with informatica_acessorios and moveis_decoracao rounding out the top 5.

Chart spec:
{'chart_type': 'bar', 'x': 'product_category_name', 'y': 'order_count', 'orientation': 'vertical', 'title': 'Top 5 Product Categories by Order Count'}

Follow-ups:
['What are the bottom 5 product categories by number of orders?', 'How do these top categories compare in total revenue rather than order count?', 'What is the average order value for each of these top 5 categories?', 'How have orders in these top categories trended over time?', 'What are the top product categories by number of distinct customers?']

verify_answer: PASSED

$ .venv/Scripts/python.exe -m evals.run
[PASS] What are the top 5 product categories by number of orders?
[PASS] Which payment type is used the most, by number of payments?
[PASS] Which customer state has the most customers?
[PASS] How many orders have the status 'delivered'?
[PASS] What is the average review score across all reviews?
[PASS] What is the average order value?
6/6 correct
```

Both exit 0. `evals.run` still 6/6 — the new mandatory `analyze_answer()`
call did not regress SQL-correctness grading.

Full suite (`python -m unittest discover tests`, 329 tests): the first
two runs this session surfaced real, live concurrency corruption in
`app.catalog_tables`/`app.kb_chunks` from a **second, concurrently-running
full-suite process** (the project's own Stop hook,
`.claude/hooks/stop_verify.py`, re-runs the full suite against the same
live Postgres DB on every turn end when watched-file content doesn't
match its last-verified signature) — never a failure in code this slice
touched. Evidence: `test_glossary_verify_embed.py`'s `UniqueViolation:
duplicate key ... (source)=(active-seller-count)` (a row this run
deleted was independently re-inserted by another process mid-test) and
`test_describe_cli.py`'s `customers` description flipping between the
real LLM text and `test_catalog_sync.py`'s temporary hand-set stub (its
own mutate-then-restore test racing a second process's identical test).
Root cause: this slice's new mandatory `analyze_answer()` call pushed
real full-suite runtime from ~250s to ~570-840s, past the Stop hook's
previous 600s subprocess timeout — on user direction, fixed as part of
this slice by bumping that timeout to 1200s
(`.claude/hooks/stop_verify.py`). Re-run fresh after the fix, solo, no
concurrent process this time:

```
$ .venv/Scripts/python.exe -m unittest discover tests
Ran 329 tests in 788.387s

OK
EXIT_CODE=0
```

DB integrity re-confirmed after this clean run: zero corrupted
descriptions, `kb_chunks` at its correct count of 16. **PASS.**

## 4. The no-slop review found no unresolved issues

no-slop-reviewer subagent dispatched against the full diff. One finding:

- **[duplication] `app/pipeline/verify_analyze_answer.py`** — after
  wiring, `get_answer()` already computes the analysis internally, but
  this script discarded that value and called `analyze_answer()` a
  second time with identical arguments, burning a redundant billed
  Anthropic call every run. **Fixed**: now unpacks `_sql, _rows, result
  = await get_answer(FIXED_QUESTION)` and calls `analyze_answer()` zero
  extra times. Re-verified: `verify_analyze_answer: PASSED`.

Everything else reported clean: no dead code, no unhandled errors, no
remaining duplication, consistent naming, the analyze-failure-propagates
-uncaught path proven by an actual test run (not just implemented), no
stale comments, `AnalyzeResponse` reused directly everywhere (never
hand-flattened), nothing outside the brief's Outputs, no stubs/TODOs.
**PASS** — the one finding fixed before this record was written.

## 5. The shipping proof is attached

Real dev server, real HTTP call, real LLM chain end-to-end (not just
tests):

```
$ .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
$ curl -s -w "\nHTTP_STATUS=%{http_code}\n" -X POST http://127.0.0.1:8000/api/ask \
    -H "Content-Type: application/json" \
    -d '{"question": "What is the average review score across all reviews?"}'

{"sql":"SELECT AVG(review_score) AS average_review_score FROM olist.order_reviews","rows":[{"average_review_score":"4.0864206240425703"}],"analysis":{"summary":"The average review score across all reviews is approximately 4.09 out of 5.","explanation":"The query computed the overall average of the review_score column across every row in olist.order_reviews, returning a single scalar value of about 4.0864, indicating that customers generally rate their orders quite favorably.","chart_spec":{"chart_type":"none","reason":"Single scalar value with no categorical or time dimension to plot; best displayed as a KPI/metric card rather than a chart."},"follow_ups":["What is the distribution of review scores (count of 1-star, 2-star, etc.)?","How does average review score vary by month or year?","Which product categories have the highest and lowest average review scores?","Is there a correlation between delivery time and review score?","Which sellers have the lowest average review scores?"]}}
HTTP_STATUS=200
```

Real, running `/api/ask` returns `analysis` alongside `sql`/`rows` in a
live HTTP response, end to end. **PASS.**

## Rejected or changed

- Rejected the test-writer's/my own first draft of
  `verify_analyze_answer.py`'s fix: initially just unpacked and discarded
  `get_answer()`'s new third element while still calling `analyze_answer()`
  a second time separately (see Check 4) — the no-slop-reviewer caught
  that this doubled the script's billed LLM cost for no reason once
  `get_answer()` already computes it. Changed to reuse `get_answer()`'s
  own analysis result.
- Added one out-of-brief fix on explicit user direction mid-gate:
  `.claude/hooks/stop_verify.py`'s subprocess timeout, 600s -> 1200s
  (Check 3's concurrency-corruption finding). Not in the brief's Outputs
  (it's test infrastructure, not the wiring), but the user chose to fix
  it now rather than carry it forward, so it ships in this same commit
  with its own clearly-scoped diff hunk.

## Verdict

**accept** — all five checks green.
