# Eval — repair failed SQL once

Slice: plans/briefs/2026-08-03-repair-loop.md
Date: 2026-08-03

## What is being checked
`prompts/repair_sql.md` + `app/pipeline/repair_sql.py`'s `repair_sql()`
produce a corrected, validation/execution-passing `SELECT` statement given
the original question, a failed SQL string, and the real error that
failure produced — for both ways `get_answer()`'s `_answer_with_repair()`
can trigger it: a `validate_sql()` rejection (never reaches the DB) and a
real execution-time failure (passes validation, fails in Postgres).
`evals/questions.yaml`'s 6/6 never exercises this prompt at all (every
question succeeds on the first `generate_sql()` try), so this is the only
eval coverage the new prompt has — required per CLAUDE.md's "a prompt
change without an eval run is not done" and `templates/no-slop.md`
item 8.

## Cases
Two fixed cases, hand-crafted to trigger each of the two ways
`_answer_with_repair()` invokes `repair_sql()`. Expected is a rubric, not
exact text, since repair output is generative:
- **R1** returns a different SQL string than the broken input
- **R2** is a single, well-formed `SELECT`
- **R3** passes a fresh, real `validate_sql()` call
- **R4** actually executes against the real read-only connection and
  returns rows (proves the fix is real, not just syntactically different)

| # | Input (question, broken SQL, real captured error) | Expected | Actual (real 2026-08-03 run) | Pass? |
|---|---|---|---|---|
| 1 | Q: "How many rows are in the orders table?" · Broken: `SELECT nonexistent_column_xyz FROM olist.orders` (real table, fake column) · Error (from `validate_sql()`): `unknown column referenced: Column 'nonexistent_column_xyz' could not be resolved. Line: 1, Col: 29` | R1-R4 | `SELECT COUNT(*) FROM olist.orders` | Pass |
| 2 | Q: "What is the average order item price relative to itself?" · Broken: `SELECT price / (price - price) AS ratio FROM olist.order_items LIMIT 5` (passes `validate_sql()`, fails at real execution) · Error (from `execute_sql()`): `division by zero` | R1-R4 | `SELECT AVG(price) / AVG(price) AS ratio FROM olist.order_items LIMIT 5` | Pass |

## Grader
Mechanical, run for real, not LLM-as-judge (rubric is structural —
"does it validate and execute" — not a business-correctness judgment call
at 2 cases): case 1's captured error was produced by a real
`validate_sql()` call against the real catalog; case 2's was produced by a
real `execute_sql()` call against the real read-only connection. Each
repaired SQL was then re-checked for real: `validate_sql()` for R2/R3, and
a real `execute_sql()` call for R4 (case 2's repaired SQL returned
`[{'ratio': Decimal('1.00000000000000000000')}, ...]` — no crash, a real
row back). Case 1's repaired SQL is executed as part of
`tests/test_answer_repair.py`'s `AnswerWithRepairEndToEndTests` (asserts
real, non-empty rows), so that case is also covered by the committed
test suite, not just this manual run.

## How to run
Manual, mirroring `evals/generate_sql.md`'s convention (no dedicated CLI
for this one-off check yet — `evals/questions.yaml`'s 6/6 is the
statistical-confidence harness; this file is the smoke check for the
repair prompt specifically, same relationship `evals/generate_sql.md` has
to it). Construct the broken-SQL/real-error pair as shown above, call
`repair_sql(question, broken_sql, error)`, then re-validate/re-execute the
result. Re-run on any change to `prompts/repair_sql.md`, `ANTHROPIC_MODEL`,
or `repair_sql.py`'s call shape.

## Result
2/2 pass, 2026-08-03, against `claude-sonnet-5`. First run, no regressions
to compare against — one case per trigger path (`validate_sql()` failure,
`execute_sql()` failure), matching the mechanism `_answer_with_repair()`
actually implements. Only 2 cases, so this is a smoke check, not
statistical confidence, same caveat `evals/generate_sql.md` (2/2) carries.
