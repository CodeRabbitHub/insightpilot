# Review gate — analyze-answer

Date: 2026-08-05
Brief: plans/briefs/2026-08-05-analyze-answer.md
Diff reviewed: working tree (uncommitted at gate time) — 8 new files
(`app/pipeline/analyze_answer.py`, `app/pipeline/verify_analyze_answer.py`,
`prompts/analyze.md`, `evals/analyze_answer.md`,
`tests/_analyze_answer_helpers.py`, `tests/test_analyze_answer.py`,
`tests/test_analyze_answer_prompt_file.py`,
`tests/test_verify_analyze_answer_script.py`) plus the brief itself and the
pre-existing, unrelated `plans/logs/_auto-capture.md` hook log.

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review
`git diff --stat HEAD` (excluding the auto-capture log):
```
app/pipeline/analyze_answer.py             |  95 ++++++++
app/pipeline/verify_analyze_answer.py      |  53 ++++
plans/briefs/2026-08-05-analyze-answer.md  |  95 ++++++++
prompts/analyze.md                         |  38 +++
tests/_analyze_answer_helpers.py           |  33 +++
tests/test_analyze_answer.py               | 374 +++++++++++++++++++++++++++++
tests/test_analyze_answer_prompt_file.py   | 152 ++++++++++++
tests/test_verify_analyze_answer_script.py |  73 ++++++
8 files changed, 913 insertions(+)
```
(`evals/analyze_answer.md`, added mid-gate — see Check 4 — is untracked and
not shown by `git diff HEAD`; it's a new ~65-line doc, read in full.) Every
file is new and single-purpose; the core implementation
(`analyze_answer.py` + `verify_analyze_answer.py`) is ~148 lines. Read line
by line. PASS.

## 2. The stated goal matches the actual change
Brief's Goal: add `analyze_answer(question, sql, rows)`, a new pipeline
step that makes one Claude call with the question, the executed SQL, and a
capped sample of its result rows, returning a Pydantic-validated
`{summary, explanation, chart_spec, follow_ups}` object.

What the diff does: `prompts/analyze.md` (new, `string.Template`, 5
placeholders: question/sql/row_count/sample_size/row_sample) instructs the
model to return that exact JSON shape. `app/pipeline/analyze_answer.py`
defines `AnalyzeResponse` (Pydantic: `summary: str`, `explanation: str`,
`chart_spec: dict[str, Any]`, `follow_ups: list[str]`, with field
validators rejecting blank summary/explanation and empty/blank
follow_ups), `build_prompt()` (caps rows to `ROW_SAMPLE_CAP = 20` before
serializing — a ceiling per PRD F1's 50-row display cap, not a target, per
the brief's own comment), `call_llm_for_analysis()` (one Anthropic call,
`extract_json_object` + Pydantic validation, exactly one retry via
`MAX_RETRIES` reused from `generate_sql.py`, raising a `RuntimeError` with
no placeholder fallback on exhausted retries — mirrors
`call_llm_for_sql()`'s exact shape), and `analyze_answer(question, sql,
rows)` (the public entrypoint, reusing `DEFAULT_MODEL`/`require_env`).
`verify_analyze_answer.py` is the done-check CLI: calls the real
`get_answer(FIXED_QUESTION)`, feeds the result into `analyze_answer()`,
asserts non-blank summary/explanation, a dict chart_spec, and a non-empty
follow_ups list.

Confirmed via `git diff`/`git status` that `app/pipeline/answer.py`,
`app/main.py`, message persistence, and every frontend file are untouched
— no wiring, matching the brief's Out-of-scope. `evals/questions.yaml`/
`evals/run.py` are untouched too (out of scope — they grade
`get_answer()`'s SQL correctness only, which `analyze_answer()` isn't
wired into). Goal and diff match. PASS.

## 3. The eval or test passed
Done-check, run fresh at gate time (after all fixes below):
```
$ .venv/Scripts/python.exe -m app.pipeline.verify_analyze_answer
Summary:
The top 5 product categories by number of orders are cama_mesa_banho (9,417), beleza_saude (8,836), esporte_lazer (7,720), informatica_acessorios (6,689), and moveis_decoracao (6,449).

Explanation:
The query joined order_items to products on product_id, grouped by product_category_name, and counted distinct order_ids per category, then sorted descending and limited to 5 rows. The sample contains all 5 returned rows, showing cama_mesa_banho (bed/bath/table items) as the leading category, followed by health & beauty, sports & leisure, computer accessories, and furniture/decor, indicating these are the most frequently ordered product types on the platform.

Chart spec:
{'chart_type': 'bar', 'x_field': 'product_category_name', 'y_field': 'order_count', 'orientation': 'vertical', 'title': 'Top 5 Product Categories by Number of Orders', 'sort': 'descending'}

Follow-ups:
['What are the bottom 5 product categories by number of orders?', 'How do these top categories compare in total revenue rather than order count?', 'What is the average order value for each of these top 5 categories?', 'How have orders in these top categories trended over time?', 'Which sellers dominate sales in the top category, cama_mesa_banho?']

verify_analyze_answer: PASSED
```
Exit 0. Dedicated test modules, run fresh:
```
$ .venv/Scripts/python.exe -m unittest discover -s tests -p "test_analyze_answer.py" -v
[... 20 tests ...]
Ran 20 tests in 31.726s
OK

$ .venv/Scripts/python.exe -m unittest discover -s tests -p "test_analyze_answer_prompt_file.py" -v
[... 12 tests ...]
Ran 12 tests in 0.018s
OK

$ .venv/Scripts/python.exe -m unittest discover -s tests -p "test_verify_analyze_answer_script.py" -v
test_verify_analyze_answer_exits_zero_for_the_fixed_question ... ok
test_verify_analyze_answer_stdout_reports_the_passed_marker ... ok
Ran 2 tests in 23.426s
OK
```
Full suite, run fresh, solo (foreground, to avoid racing the automatic
Stop hook's own concurrent run per the repair-loop slice's documented
lesson):
```
$ .venv/Scripts/python.exe -m unittest discover tests
Ran 304 tests in 666.073s
OK
```
304 = the prior 301 (from a first fresh full run, taken *before* the
fixes below) + 3 new (`BuildPromptRowCappingTests`). No eval-harness run
(`evals.run`) — out of scope per the brief, `analyze_answer()` isn't wired
into that call path. PASS.

**One real bug caught and fixed by this same full-suite run, not a flaky
retry:** the first full-suite attempt failed
`test_a_row_sample_larger_than_a_small_sample_does_not_raise` with
`RuntimeError("LLM failed to produce a valid analysis after 2 attempt(s):
'ThinkingBlock' object has no attribute 'text'")`. Root cause:
`call_llm_for_analysis()` read `response.content[0].text`, assuming the
first content block is always text — Claude can prepend a `ThinkingBlock`
(no `.text` attribute) ahead of the text block, and since both retry
attempts hit the same model behavior for this input, both failed
identically. Fixed by adding `_extract_response_text(response)`, which
scans `response.content` for the first block with `type == "text"` instead
of indexing `[0]`. Re-ran the specific test and the full suite again after
the fix — both clean (see above; the "304 tests" run above is the
post-fix run). This exact fragile pattern still exists unfixed in
`app/pipeline/generate_sql.py`, `app/pipeline/repair_sql.py`, and
`app/catalog/describe.py` — flagged as a known, pre-existing, out-of-scope
issue for this slice (only this slice's own new file was fixed); worth a
future slice if it recurs.

## 4. The no-slop review found no unresolved issues
Round 1 (`no-slop-reviewer` subagent, first pass): four findings.
1. **[Scope]** `prompts/analyze.md` had no matching `evals/*.md` case. The
   brief's Out-of-scope note only justified skipping the automated
   `evals/questions.yaml` harness, not the manual-eval-doc precedent
   `evals/repair_sql.md` set for exactly this situation (another
   one-Claude-call step not wired into the graded harness). **Fixed:**
   added `evals/analyze_answer.md` — two real cases (the FIXED_QUESTION
   grouped result, and a real scalar-result case chosen specifically to
   exercise the prompt's "don't fabricate axes for a non-chartable result"
   instruction; its `chart_spec` came back `{}`).
2. **[Untested edges]** The row-cap Constraint was only tested
   behaviorally (a 200-row input doesn't crash), never structurally — a
   regression that deleted the capping entirely would still pass. **Fixed:**
   added `BuildPromptRowCappingTests` (pure, no-network): asserts the
   prompt's embedded JSON sample equals `rows[:ROW_SAMPLE_CAP]` exactly,
   that the true total row count is still reported alongside the capped
   sample, and that an empty row list doesn't raise.
3. **[Unhandled errors / Consistency]** `verify_analyze_answer.py` had no
   `try/except`, diverging from `verify_answer.py`'s
   print-FAILED-and-exit-1 convention on a real failure. **Fixed:** wrapped
   the `get_answer()` + `analyze_answer()` calls in
   `try/except (SqlValidationError, RuntimeError)`, matching
   `verify_answer.py`'s exact shape (`RuntimeError` added since that's
   `analyze_answer()`'s own raised exception type on exhausted retries).
4. **[Untested edges, minor]** No zero-row case. **Fixed:** covered by
   `test_build_prompt_handles_an_empty_row_list_without_raising` (pure
   function-level coverage of `build_prompt()`, not a full live-call
   zero-row `analyze_answer()` case — accepted as sufficient, a real
   zero-row live case would need a hand-crafted always-empty query, a
   bigger ask than this slice's scope).

Round 2 (fresh `no-slop-reviewer` pass over the corrected diff, including
the independently-discovered `_extract_response_text` fix from Check 3):
re-verified all five fixes are real (not just claimed) — re-ran the
done-check and the analyze_answer test modules fresh, cross-checked
`evals/analyze_answer.md`'s case 1 numbers against a live run (exact
match), confirmed the row-cap tests aren't tautological, confirmed
`generate_sql.py`/`describe.py` were correctly left untouched (not
silently duplicating the fix or the bug). One cosmetic-only note (no fix
required): `BuildPromptRowCappingTests` lives in `test_analyze_answer.py`
as intended — the reviewer's own summary misstated its file location, a
transcription slip, not a real finding. Zero unresolved findings. **Verdict:
clean.** PASS.

## 5. The shipping proof is attached
Two real, billed chains (each: two Voyage embeds via `get_answer()` +
`generate_sql()`'s retrieval, plus two Anthropic calls — `generate_sql()`
then `analyze_answer()`), against the real seeded `olist` database:

**Case 1 — grouped result** (`FIXED_QUESTION`, done-check output above):
5 rows, `cama_mesa_banho` first at 9,417 — summary/explanation state every
number correctly, `chart_spec` proposes a real bar-chart mapping, 5
follow-ups.

**Case 2 — single-scalar result** ("How many orders have the status
'delivered'?", `evals/analyze_answer.md`'s second case, independently
matching `evals/questions.yaml`'s verified `96478`):
```
SQL: SELECT COUNT(*) FROM olist.orders WHERE order_status = 'delivered'
Rows: [{'count': 96478}]
Summary: There are 96,478 orders with the status 'delivered'.
Chart spec: {}
Follow-ups: [4 real questions]
```
Proves the prompt's explicit "don't fabricate axes for a non-chartable
result" instruction actually holds against a real, non-fabricated model
response — `chart_spec` came back a genuinely minimal `{}`, not an invented
bar/line mapping for a single number.

Both cases are real, live, non-mocked evidence of the module working end
to end, not just passing an assertion. PASS.

## Rejected or changed
Three things changed from the first draft, all found by the process
itself, not rubber-stamped:
1. Added `evals/analyze_answer.md` (not in the original brief's Outputs
   list) — required by no-slop item 8 / CLAUDE.md's standing rule, caught
   by the round-1 no-slop pass.
2. Added `BuildPromptRowCappingTests` (3 new pure tests) — the original
   test suite proved the row-cap Constraint behaviorally but never
   structurally; caught by the round-1 no-slop pass.
3. Fixed a real `ThinkingBlock`/`response.content[0].text` bug in
   `call_llm_for_analysis()` — caught by the full test suite itself (not
   the no-slop pass), fixed with a small `_extract_response_text()` helper
   scoped only to this slice's own new file; the same fragile pattern
   remains unfixed in three sibling modules, explicitly left alone as
   out of scope for this slice.
Also added the `try/except` convention fix (round-1 no-slop finding 3) and
the empty-row test (finding 4) — both folded into the same round of edits.

## Verdict
accept — all five checks green.
