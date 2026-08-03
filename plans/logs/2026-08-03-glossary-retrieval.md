# Slice log — business glossary retrieval

Date: 2026-08-03
Brief: plans/briefs/2026-08-03-glossary-retrieval.md

## The plan you approved
Mirror the pgvector-schema-retrieval slice's exact pattern for a second
knowledge source: a new `glossary.md` (16 hand-verified KPI definitions),
embedded via a new `app/glossary/` package that reuses (never reinvents)
`app/catalog/embed.py`'s Voyage client/retry/upsert conventions, into a new
`app.kb_chunks` table (name and shape already implied by PRD.md's Data
Model section and reserved by a prior slice's own tests). `generate_sql()`
gains `retrieve_relevant_glossary_entries()`, analogous to but independent
of `retrieve_relevant_tables()`, threaded through `build_prompt()`/
`call_llm_for_sql()` alongside the existing schema context. Known,
accepted tradeoff going in: the question gets embedded twice per call
(schema + glossary), since the brief keeps `retrieve_relevant_tables()`'s
own signature out of scope.

## The diff you accepted
Commit `a000513` — "Business glossary retrieval: pgvector KPI context
alongside schema context." 21 files changed, 1537 insertions(+), 29
deletions(-). Full stat in `plans/logs/_auto-capture.md`. Gate record:
`artifacts/reviews/2026-08-03-glossary-retrieval.md` (accept, all five
checks green).

A second, disclosed follow-up commit made during this capture step:
`dd3c561` — adds a 6th eval question (average order value) and unpins two
tests that had hardcoded "exactly 5"/"N/5" assumptions (see "One thing you
rejected or changed" below).

## The done-check output
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
............................................................................................................................................................................
----------------------------------------------------------------------
Ran 172 tests in 219.629s

OK
```
(Full gate detail — including the mid-slice eval regression, 7
full-suite attempts, and the two distinct hazard classes that caused 5 of
them — in `artifacts/reviews/2026-08-03-glossary-retrieval.md`.)

## One thing you rejected or changed
While verifying this slice's own done-check, running the eval fresh
(rather than trusting the code looked right) caught a real regression:
the first draft of `glossary.md`'s "Top Product Category" and "Repeat
Purchase Rate" KPI entries were too prescriptive and leaked into unrelated
questions — steering the LLM to use `COUNT(*)` with translated category
names (instead of `COUNT(DISTINCT order_id)` with the untranslated name
the eval's ground truth uses) and to always group customers by
`customer_unique_id`, even for a plain "count customers by state"
question where that's wrong. This dropped the eval from 5/5 to 3/5.
Diagnosed by comparing generated SQL against direct DB queries, rewrote
both entries to explicitly scope their guidance to the KPI they actually
define, deleted and re-embedded the two affected `app.kb_chunks` rows
(no new cache-invalidation logic — just the existing idempotent script,
re-run against corrected source content), and reconfirmed 5/5 twice
before moving on.

Separately, while writing this capture log I added a 6th eval question
(average order value) specifically to exercise a KPI whose correct SQL
depends on glossary context, since none of the original 5 questions
happened to test that path directly — they caught the regression above by
accident (two of them incidentally touch categories/customers), not
because any of them specifically stresses glossary-informed KPI
computation. That addition broke two tests with hardcoded "exactly
5"/"N/5" assumptions (`test_eval_questions_yaml.py`,
`test_eval_run_cli.py`); both were checking a premise the eval set's own
documented lifecycle ("start with 5; every production/demo failure adds a
case," per `templates/eval.md`) always intended to outgrow, so they were
loosened to "at least 5" / "N/M" rather than weakened in what they
actually verify.

**Ratchet promoted:** Voyage's free-tier 3 RPM rate limit caused real
failures for the third consecutive slice (this time: `RATE_LIMIT_MAX_ATTEMPTS`
4→6, plus three timeout bumps, after a real full-suite run hit a genuine
`RateLimitError` exhaustion). Per direct sign-off, promoted from a
per-slice comment to a CLAUDE.md standing rule: any future change adding
a new Voyage/Anthropic call site must budget for rate-limit contention in
the same slice.

Also per direct sign-off during the gate: encountered the pre-existing,
HANDOFF-documented Stop-hook/shared-DB-row concurrency hazard 5 times
across 7 full-suite attempts this session (confirmed via a real Postgres
deadlock in an unrelated M1-era test, proving genuine concurrent overlap,
not a code defect). Did not chase a fix — it's explicitly out-of-scope for
this slice, and the user chose to retry once more (which succeeded)
rather than open that investigation now.

## The next smallest slice
The one-shot repair loop (PRD F2/F3): when `validate_sql.py` rejects a
generated SQL statement or the real DB execute fails, feed the error back
to the LLM via a new `prompts/repair_sql.md` for one corrected retry (max
2 attempts total, matching `generate_sql()`'s own `MAX_RETRIES` shape).
This closes out M3 (retrieval + repair + evals) entirely — schema and
glossary retrieval are both live, and the eval harness (now 6 questions)
gives a concrete accuracy baseline to check the repair loop against.
