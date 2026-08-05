# Eval — analyze_answer summary/explanation/chart_spec/follow_ups

Slice: plans/briefs/2026-08-05-analyze-answer.md
Date: 2026-08-05

## What is being checked
`prompts/analyze.md` + `app/pipeline/analyze_answer.py`'s `analyze_answer()`
produce a grounded `summary`/`explanation`, a reasonable `chart_spec`, and
3-5 real `follow_ups` given a real question, its real generated SQL, and a
real result-row sample from `get_answer()`. `evals/questions.yaml`'s 6/6
never exercises this prompt at all (it grades `get_answer()`'s SQL
correctness only, and `analyze_answer()` isn't wired into that call path
this slice — see the brief's Out-of-scope), so this is the only eval
coverage the new prompt has, required per CLAUDE.md's "a prompt change
without an eval run is not done" and `templates/no-slop.md` item 8 —
mirroring `evals/repair_sql.md`'s precedent for `repair_sql.py`, another
one-Claude-call pipeline step not wired into the graded harness.

## Cases
Two real cases chained through the real pipeline (`get_answer()` then
`analyze_answer()`, two Voyage embeds + two Anthropic calls each),
deliberately chosen for contrasting result shapes: a multi-row grouped
result and a single-row/single-column scalar result, since the prompt
explicitly instructs "if the result isn't meaningfully chartable ... return
a minimal object rather than fabricate axes." Grading is a rubric (summary
states the actual number(s), explanation is grounded in the real rows,
chart_spec is a shape appropriate to the result, follow_ups are 3-5 real
questions), not exact-match, since this output is generative.

| # | Question | SQL / rows | Summary | Chart spec | Follow-ups (count) | Grounded? | Pass? |
|---|---|---|---|---|---|---|---|
| 1 | `FIXED_QUESTION` ("top 5 product categories by number of orders") | `SELECT p.product_category_name, COUNT(DISTINCT oi.order_id) ... GROUP BY ... ORDER BY ... LIMIT 5` → 5 rows, `cama_mesa_banho` first at 9,417 | "The top 5 product categories by number of orders are cama_mesa_banho (9,417), beleza_saude (8,836), esporte_lazer (7,720), informatica_acessorios (6,689), and moveis_decoracao (6,449)." | `{'chart_type': 'bar', 'x': 'product_category_name', 'y': 'order_count', 'orientation': 'vertical', 'title': 'Top 5 Product Categories by Number of Orders'}` | 5 | Yes — every category name and count matches the real rows exactly | Pass |
| 2 | "How many orders have the status 'delivered'?" (`evals/questions.yaml`'s own scalar case, independently verified `96478`) | `SELECT COUNT(*) FROM olist.orders WHERE order_status = 'delivered'` → `[{'count': 96478}]` | "There are 96,478 orders with the status 'delivered'." | `{}` | 4 | Yes — the count matches the verified value exactly | Pass |

## Grader
Manual, rubric-based (not mechanical/exact-match like `evals/questions.yaml`,
since `summary`/`explanation`/`follow_ups` are generative text and
`chart_spec` has no fixed schema this slice — brief's Constraints). Each
case checked for: (a) the summary's stated number(s) match the real
executed rows exactly, (b) the explanation references the actual query
shape/values rather than generic filler, (c) `chart_spec` is a dict
appropriate to the result shape — a real bar-chart mapping for the
multi-row case, and a deliberately minimal `{}` for the single-scalar case
rather than fabricated axes (exactly what the prompt instructs for a
non-chartable result), (d) `follow_ups` has 3-5 nonblank, on-topic
questions answerable from the same `olist` schema. Both cases pass every
criterion above.

## How to run
Manual, mirroring `evals/repair_sql.md`'s convention (no dedicated CLI for
this one-off rubric check yet — `evals/questions.yaml`'s N/M is the
statistical-confidence harness for SQL correctness; this file is the smoke
check for the analyze prompt specifically). Call `get_answer(question)` to
get a real `(sql, rows)` pair, then `analyze_answer(question, sql, rows)`,
and check the result against the rubric above. Re-run on any change to
`prompts/analyze.md`, `ANTHROPIC_MODEL`, or `analyze_answer.py`'s call
shape.

## Result
2/2 pass, 2026-08-05, against `claude-sonnet-5`. First run, no regressions
to compare against — one grouped-result case and one scalar-result case,
chosen to exercise the prompt's explicit "don't fabricate axes for a
non-chartable result" instruction. Only 2 cases, so this is a smoke check,
not statistical confidence, same caveat `evals/repair_sql.md` (2/2) and
`evals/generate_sql.md` (2/2) carry.
