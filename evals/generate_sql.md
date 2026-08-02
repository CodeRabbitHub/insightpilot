# Eval — generate SQL from a fixed question

Slice: plans/briefs/2026-08-02-generate-sql.md
Date: 2026-08-02

## What is being checked
`prompts/generate_sql.md` + `app/pipeline/generate_sql.py` produce a
single, correct SQL `SELECT` statement for one fixed business question,
using the full `olist` catalog (all 9 tables' DDL + description +
columns) as context, with no retrieval and no execution in the pipeline
itself.

## Cases
One fixed case (this slice hardcodes exactly one question, per the
brief). Expected is a rubric, not exact text, since SQL generation is
generative:
- **R1** references only real `olist.*` tables/columns (no hallucinated
  name)
- **R2** joins `order_items` to `products` correctly to get the category
  per order line
- **R3** counts orders, not order line items — must use
  `COUNT(DISTINCT order_id)` (or equivalent) so a multi-item order in one
  category isn't counted more than once
- **R4** groups by category, orders descending, and limits to 5 (the
  question's "top 5")

| # | Input (question) | Expected | Actual (from the real 2026-08-02 run) | Pass? |
|---|---|---|---|---|
| 1 | "What are the top 5 product categories by number of orders?" | R1-R4 | `SELECT p.product_category_name, COUNT(DISTINCT oi.order_id) AS num_orders FROM olist.order_items oi JOIN olist.products p ON oi.product_id = p.product_id GROUP BY p.product_category_name ORDER BY num_orders DESC LIMIT 5` | Pass |

## Grader
Two-part: (1) `verify_generate_sql`'s live catalog check confirms R1
mechanically (real table/column names, alias-aware). (2) The SQL was then
executed directly against the real `olist` database (a one-off manual
check for this eval, outside the pipeline — the pipeline itself never
executes generated SQL, per the brief's out-of-scope) to confirm R2-R4
produce a sane, correctly-ordered result:
```
('cama_mesa_banho', 9417)
('beleza_saude', 8836)
('esporte_lazer', 7720)
('informatica_acessorios', 6689)
('moveis_decoracao', 6449)
```
Five rows, strictly descending by count, `COUNT(DISTINCT oi.order_id)`
correctly avoids inflating counts from multi-item orders. Human review
against R1-R4 above (LLM-as-judge not justified at one fixed case; revisit
once this eval set grows past what's easy to read by hand — same
threshold `evals/table_description.md` used).

## How to run
Manual: `python -m app.pipeline.verify_generate_sql`, then read the
printed SQL against R1-R4 (optionally execute it against the real DB to
confirm the result set, as done above). Re-run this whole set on any
change to `prompts/generate_sql.md` or `ANTHROPIC_MODEL`.

## Result
1/1 pass, 2026-08-02, against `claude-sonnet-5`. First run for this eval —
no regressions to compare against yet.
