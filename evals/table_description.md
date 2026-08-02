# Eval — catalog table descriptions

Slice: plans/briefs/2026-08-02-llm-table-descriptions.md
Date: 2026-08-02

## What is being checked
`prompts/table_description.md` + `app/catalog/describe.py` produce a
genuinely useful, accurate, table-specific paragraph for a business
analyst — not a generic or hallucinated one — for every table in the
`olist` schema.

## Cases
Real inputs: the 9 actual `olist` tables (all of them — this is a small,
fixed catalog, not a sample). Expected is a rubric, not exact text, since
the task is generative:
- **R1** correctly states what one row represents
- **R2** calls out the real PK/FK relationships evident from the DDL
  (or correctly notes the absence of any, for the one table with none)
- **R3** is specific to this table, not generic boilerplate reusable for
  any table
- **R4** reads as a genuine paragraph, no hallucinated column names

| # | Input (table) | Expected | Actual (from the real 2026-08-02 run) | Pass? |
|---|---|---|---|---|
| 1 | customers | R1-R4 | Correctly distinguishes `customer_id` (per-order) from `customer_unique_id` (per-person) — a real Olist modeling subtlety, not restated from the DDL | Pass |
| 2 | geolocation | R1-R4 | Correctly notes multiple rows per zip prefix and that it's a reference table with no direct transaction link | Pass |
| 3 | order_items | R1-R4 | Correctly identifies the `(order_id, order_item_id)` composite key and both FK-like links (product, seller) | Pass |
| 4 | order_payments | R1-R4 | Correctly explains `payment_sequential` for multi-method payments on one order | Pass |
| 5 | order_reviews | R1-R4 | Correctly notes an order can receive more than one review | Pass |
| 6 | orders | R1-R4 | Correctly lists the real lifecycle timestamp columns and their purpose | Pass |
| 7 | product_category_name_translation | R1-R4 | Correctly identifies it as a pure lookup table with **no PK/FK** — the one table where R2 means confirming absence, and it does | Pass |
| 8 | products | R1-R4 | Correctly notes it holds no pricing/inventory data, only descriptive/physical attributes | Pass |
| 9 | sellers | R1-R4 | Correctly notes no direct link to customers/orders, only reachable via `order_items` | Pass |

## Grader
Human review against the R1-R4 rubric above (LLM-as-judge not justified
yet at 9 fixed cases; revisit if this eval set grows past what's easy to
read by hand).

## How to run
Manual: `python -m app.catalog.sync && python -m app.catalog.describe`
against a catalog with all descriptions NULL, then read each
`app.catalog_tables.description` against R1-R4. Re-run this whole set on
any change to `prompts/table_description.md` or `ANTHROPIC_MODEL`.

## Result
9/9 pass, 2026-08-02, against `claude-sonnet-5`. First run for this eval
— no regressions to compare against yet.
