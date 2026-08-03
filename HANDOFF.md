# Handoff

Date: 2026-08-03
Slice just completed: plans/briefs/2026-08-03-glossary-retrieval.md +
  plans/logs/2026-08-03-glossary-retrieval.md (commits a000513, dd3c561,
  e80546e)

## State of the work
- **`generate_sql()` now retrieves business-glossary context alongside
  schema context, via pgvector, for every question.** `glossary.md` (16
  KPI definitions: Revenue, AOV, Repeat Purchase Rate, Average Delivery
  Time, On-Time Delivery Rate, Average Review Score, Low Review Rate,
  Churn Proxy, Freight Ratio, Average Items per Order, Order Cancellation
  Rate, Order Approval Time, Average Payment Installments, Active Seller
  Count, Top Product Category, Payment Type Mix) is embedded into a new
  `app.kb_chunks(id, source, content, embedding vector(1024))` table by a
  new `app/glossary/` package (`embed.py` + `verify_embed.py`), mirroring
  `app/catalog/embed.py`'s exact convention — same Voyage client,
  `embed_text`/`to_vector_literal`/`VOYAGE_MODEL`/`EMBEDDING_DIMENSION`
  imported, not reimplemented. `generate_sql.py` gained
  `retrieve_relevant_glossary_entries(cur, voyage_client, question,
  k=GLOSSARY_RETRIEVAL_K=3)` and `build_glossary_context()`, called
  alongside the existing `retrieve_relevant_tables()`/
  `build_schema_context()` inside `generate_sql()`. `prompts/generate_sql.md`
  gained a real `$glossary_context` templated section.
- **A real regression was caught and fixed by running the eval fresh,
  not by trusting the code looked right.** The first draft of
  `glossary.md`'s "Top Product Category" and "Repeat Purchase Rate"
  entries were too prescriptive and leaked into unrelated questions
  (steering the LLM toward `COUNT(*)` + translated category names, and
  toward always grouping by `customer_unique_id` even for a plain
  "count customers by state" question) — dropped the eval from 5/5 to
  3/5. Rewrote both entries to explicitly scope their guidance, deleted
  and re-embedded the two affected `app.kb_chunks` rows, reconfirmed 5/5
  twice. Full detail: `artifacts/reviews/2026-08-03-glossary-retrieval.md`.
- **The eval set grew to 6 questions.** Added "What is the average order
  value?" (`expected.scalar: 137.7541, tolerance: 0.01`, hand-verified
  live) specifically because none of the original 5 questions directly
  exercises glossary-informed KPI computation — they only caught the
  regression above by accident. Two tests that had hardcoded "exactly
  5"/"N/5" assumptions (`tests/test_eval_questions_yaml.py`,
  `tests/test_eval_run_cli.py`) were loosened to "at least 5"/"N/M",
  since the eval set's own documented lifecycle
  (`templates/eval.md`: "start with 5; every production/demo failure
  adds a case") always intended growth past 5.
- **Voyage's free-tier 3 RPM rate limit caused a real failure for the
  3rd consecutive slice**, now promoted from a per-slice comment to a
  CLAUDE.md standing rule: any future change adding a new Voyage/
  Anthropic call site must budget for rate-limit contention in the same
  slice. Concretely this slice: `RATE_LIMIT_MAX_ATTEMPTS` 4→6
  (`app/catalog/embed.py`, shared/reused by `app/glossary/embed.py`);
  `stop_verify.py`'s subprocess timeout 1200s→2400s;
  `tests/_answer_helpers.py`'s/`tests/_generate_sql_helpers.py`'s own
  subprocess timeouts 120s→450s; CLAUDE.md's documented real test
  runtime ~15min→~30min. Root cause: `generate_sql()` now makes two
  independent Voyage embed calls per question (schema + glossary), a
  known, accepted, in-code-documented tradeoff — the brief kept
  `retrieve_relevant_tables()`'s own signature out of scope, so the two
  calls can't share one embedding.
- Both done-checks pass fresh, most recent run:
  ```
  $ python -m evals.run
  [PASS] What are the top 5 product categories by number of orders?
  [PASS] Which payment type is used the most, by number of payments?
  [PASS] Which customer state has the most customers?
  [PASS] How many orders have the status 'delivered'?
  [PASS] What is the average review score across all reviews?
  [PASS] What is the average order value?
  6/6 correct
  ```
  ```
  $ python -m unittest discover tests
  Ran 172 tests in 219.629s

  OK
  ```
- Real, live shipping proof beyond the curated eval questions: asking
  "What is the average order value?" retrieved the `average-order-value-aov`
  glossary entry as the top hit and generated
  `SELECT SUM(price) / COUNT(DISTINCT order_id) AS average_order_value
  FROM olist.order_items`, which executed to a real `137.7540763788944520`
  — matching the KPI's own formula exactly.

## Proof
See the two command blocks above (`evals.run`, `unittest discover tests`).
Both were run fresh, standalone, this session, on the final committed
state.

## Open questions / known issues
- **The pre-existing Stop-hook/shared-mutable-DB-row concurrency hazard
  (first documented in the eval-harness-v1 handoff) is still unresolved
  and still out of scope.** It recurred repeatedly this session: 5 of 7
  full-suite attempts failed on it, in three different shapes — the
  known `customers`-description race, a *new* instance of the same
  pattern on `app.kb_chunks` (`tests/test_glossary_verify_embed.py`'s own
  mutate-restore-in-`finally` test hit a `UniqueViolation` when a
  concurrent run's restore raced it), and a genuine Postgres deadlock in
  `test_seed_idempotency.py` (an M1-era test with zero connection to this
  slice's code) that is direct proof two full-suite invocations
  genuinely overlapped in time. If a future session sees a similar
  mutate-restore test fail with a `UniqueViolation`/duplicate-key error,
  or `customers`'s description show up as a stub, this is why — repair
  the specific row (`UPDATE ... SET description = NULL` +
  `python -m app.catalog.describe` for `customers`; re-run
  `python -m app.glossary.embed` after deleting the affected
  `app.kb_chunks` row(s) if one goes missing) rather than touching test
  logic. A real fix (a stop_verify lock file, or giving the shared-row
  tests their own isolated row) remains a dedicated slice of its own —
  now overdue given it has cost real time in two consecutive sessions.
- The doubled-Voyage-call-per-question design cost (schema + glossary
  each independently embed the same question text) remains unoptimized
  — accepted, documented in code (`app/pipeline/generate_sql.py`'s
  `generate_sql()`), not a blocker.
- Lint/type tooling (`ruff`, `mypy`) and the test runner (`unittest`, not
  `pytest`) remain unaddressed, carried over from every prior slice —
  still not blocking.

## Next slice (the brief, written NOW while context is hot)
Goal:
When generated SQL fails `validate_sql()` or the real DB execute in
`get_answer()`, automatically retry exactly once via a new `repair_sql()`
call (the original question + the failed SQL + the real error fed to the
LLM) before giving up — per PRD F2's "one automatic repair loop, max 2
attempts total" and F9's `repair_sql.md` prompt. This closes out M3
(retrieval + repair + evals) entirely.

Constraints:
New `prompts/repair_sql.md`, `string.Template`-based like
`prompts/generate_sql.md` (placeholders for the question, the failed SQL,
and the real error text). New `repair_sql()` function (exact module
location — `app/pipeline/generate_sql.py` alongside `call_llm_for_sql()`,
or a new `app/pipeline/repair_sql.py` — proposed and confirmed at Gate 1)
reusing the existing `GenerateSqlResponse` Pydantic model (repair also
produces a single `{"sql": ...}` SELECT) and the existing Anthropic
client/`require_env` pattern — no new provider, no new response schema.
`get_answer()` in `app/pipeline/answer.py` gains the retry orchestration:
on `SqlValidationError` from `validate_sql()` or a real exception from
`execute_sql()`, call `repair_sql()` once with the concrete error
message, re-validate and re-execute the repaired SQL; if that also
fails, propagate the second failure — exactly one repair attempt, never
a loop-until-success. Must not change `retrieve_relevant_tables()`/
`retrieve_relevant_glossary_entries()`/`build_schema_context()`/
`build_glossary_context()`/`generate_sql()`'s own generation behavior,
and must not change `validate_sql.py`'s/`execute_sql.py`'s validation or
execution rules themselves — this slice only wires a retry around them.

Inputs:
PRD.md F2 (pipeline step 4: "Validate — see F3. On failure, one automatic
repair loop, max 2 attempts total"), F3 (validation rules), F9/section 9
(`repair_sql.md`: "failed SQL + DB error → corrected SELECT");
`app/pipeline/generate_sql.py` (`GenerateSqlResponse`, `call_llm_for_sql()`
pattern, `PROMPT_TEMPLATE` convention, `MAX_RETRIES` shape to mirror at
the repair-attempt-count level); `app/pipeline/validate_sql.py`
(`SqlValidationError`); `app/pipeline/execute_sql.py`; `app/pipeline/answer.py`
(`get_answer()`, the exact orchestration point to modify);
`evals/questions.yaml` + `evals/run.py` (prove no regression from the
current 6/6).

Outputs:
- `prompts/repair_sql.md`.
- A new `repair_sql()` function (module confirmed at Gate 1).
- `get_answer()` gains the one-shot repair-on-failure orchestration
  described above.
- Tests: a real, hand-crafted-invalid-SQL + real-error integration test
  proving `repair_sql()` alone returns a different, validation-passing
  SELECT (no mocking, per this project's real-infra convention) —
  mirroring how `validate_sql.py`'s own tests construct real bad SQL
  rather than mocking sqlglot; an integration test proving `get_answer()`
  actually invokes the repair path and succeeds when the *first*
  `generate_sql()` result would fail (this will need a concrete way to
  force a real, first-attempt failure without mocking — worth discussing
  explicitly at Gate 1, since `generate_sql()` with retrieval usually
  produces valid SQL); `evals/run.py`'s score re-reported (still 6/6, or
  an honestly different number with an explanation).

Done-check:
A dedicated repair-path test demonstrates the loop actually fires and
self-corrects on a real, deliberately invalid SQL + real
validation/DB error — paste output. Separately, `python -m evals.run`
exits 0 and reports its score (no regression from 6/6) — paste output.
Separately, `python -m unittest discover tests` passes in full — paste
output (expect ~20-30 min real runtime per CLAUDE.md; not hung).

Out-of-scope:
Changing `generate_sql()`'s/retrieval's own behavior; changing
`validate_sql.py`'s/`execute_sql.py`'s validation/execution rules
themselves (only wiring a retry around them); more than one repair
attempt (no loop-until-success, per PRD's explicit "max 2 attempts
total"); FastAPI/frontend (M4/M5); CI; fixing the Stop-hook/shared-DB-row
concurrency hazard noted above (still a real, separate, dedicated slice
of its own — now overdue).
