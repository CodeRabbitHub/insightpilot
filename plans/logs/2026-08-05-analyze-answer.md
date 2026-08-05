# Slice log — analyze-answer

Date: 2026-08-05
Brief: plans/briefs/2026-08-05-analyze-answer.md

## The plan you approved
Add `analyze_answer(question, sql, rows)`, a new pipeline step mirroring
`generate_sql.py`'s exact call pattern (one Anthropic call,
`extract_json_object` + Pydantic validation, one retry, no placeholder
fallback), returning `{summary, explanation, chart_spec, follow_ups}`.
Rows capped to `ROW_SAMPLE_CAP = 20` before serializing into the new
`prompts/analyze.md`. Deliberately not wired into `get_answer()`,
`app/main.py`, persistence, or the frontend — proven standalone via
`verify_analyze_answer.py`, same pattern `generate_sql.py` itself
originally followed.

## The diff you accepted
Commit `027a7cf` — "Add analyze_answer pipeline step:
summary/explanation/chart_spec/follow_ups". 10 files, 1204 insertions:
`app/pipeline/analyze_answer.py`, `app/pipeline/verify_analyze_answer.py`,
`prompts/analyze.md`, `evals/analyze_answer.md`,
`artifacts/reviews/2026-08-05-analyze-answer.md`,
`plans/briefs/2026-08-05-analyze-answer.md`, and four test files. Full
commit mechanics in `plans/logs/_auto-capture.md`. Gate record (all five
checks green, verdict accept): `artifacts/reviews/2026-08-05-analyze-answer.md`.

## The done-check output
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
Full suite, run fresh, solo/foreground: `Ran 304 tests in 666.073s / OK`.
Full details, including the pre-fix failure this run caught, in the gate
record.

## One thing you rejected or changed
The full test suite itself (not the no-slop pass) caught a real bug mid-gate:
`call_llm_for_analysis()` read `response.content[0].text`, assuming the
first content block is always text. A real call returned a `ThinkingBlock`
first instead (no `.text` attribute), so both retry attempts failed
identically with the same `AttributeError`. Fixed with a new
`_extract_response_text()` helper that scans for the first `type ==
"text"` block instead of indexing `[0]`. This exact fragile pattern still
exists, unfixed, in `generate_sql.py`, `repair_sql.py`, and `describe.py`
— left alone as pre-existing and out of scope for this slice, but this is
the first time it's actually broken a run; if it recurs in any of those
three, promote a shared `extract_response_text()` helper into
`app/catalog/describe.py` (next to `extract_json_object`) instead of
patching each site separately.

The no-slop pass separately caught and fixed three more real gaps before
accept: no `evals/*.md` case for the new prompt (added
`evals/analyze_answer.md`, two real cases, including a single-scalar
result proving `chart_spec` isn't fabricated when nothing is chartable);
the row-cap Constraint was only tested behaviorally, not structurally
(added `BuildPromptRowCappingTests`, asserting the prompt's embedded
sample is exactly `rows[:ROW_SAMPLE_CAP]`); and `verify_analyze_answer.py`
had no `try/except` matching `verify_answer.py`'s PASSED/FAILED
convention (added). None of these four findings is a new repeated
pattern warranting a `CLAUDE.md`/`templates/no-slop.md` promotion this
slice: the missing-eval-for-new-prompt shape is already promoted
(no-slop.md item 8, first caught 2026-08-02 generate-sql); the other three
are each a first occurrence in this project.

## The next smallest slice
Wire `analyze_answer()` into the full pipeline: extend `get_answer()` to
also return the `AnalyzeResponse` (or its fields), thread it through
`app/main.py`'s `AskResponse`/SSE payloads and message persistence — the
frontend itself (chart rendering, the "View SQL" section, follow-up chips)
stays out of scope for that slice too, matching how `generate_sql.py` was
wired into `get_answer()` only after `validate_sql.py`/`execute_sql.py`
each proved themselves standalone first.
