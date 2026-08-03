# Review gate — business glossary retrieval

Date: 2026-08-03
Brief: plans/briefs/2026-08-03-glossary-retrieval.md
Diff reviewed: working tree, pre-commit (9 modified files + 8 new files)

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review

```
 .claude/hooks/stop_verify.py           | 25 ++++++++------
 CLAUDE.md                              |  4 ++-
 app/catalog/embed.py                   | 11 +++++-
 app/pipeline/generate_sql.py           | 40 ++++++++++++++++++---
 prompts/generate_sql.md                |  3 ++
 tests/_answer_helpers.py               | 10 +++++-
 tests/_generate_sql_helpers.py         | 10 +++++-
 tests/test_describe_cli.py             | 48 ++++++++++++++++++++------
 tests/test_generate_sql_prompt_file.py | 63 ++++++++++++++++++++++++++++++++++
 9 files changed, 185 insertions(+), 29 deletions(-)
```
Plus 8 new files (~1170 lines): `app/glossary/__init__.py`, `app/glossary/embed.py`,
`app/glossary/verify_embed.py`, `glossary.md`, `plans/briefs/2026-08-03-glossary-retrieval.md`,
`tests/_glossary_helpers.py`, `tests/test_glossary_embed.py`, `tests/test_glossary_parsing.py`,
`tests/test_glossary_retrieval.py`, `tests/test_glossary_verify_embed.py`.

**PASS.** Read every line of the modified-file diff and the new files during the session
(new `app/glossary/` package mirrors `app/catalog/`'s reviewed shape line-for-line; new
tests mirror existing conventions). Reviewable, matches the prior slice's scale.

## 2. The stated goal matches the actual change

Brief's Goal: *"For the fixed question (and every `evals/questions.yaml` question),
`generate_sql()`'s prompt context includes top-k relevant business-glossary entries (KPI
definitions), retrieved via pgvector alongside the existing top-k schema context, with no
regression in `evals/run.py`'s current 5/5 score."*

What the diff does: adds `glossary.md` (16 KPI definitions), `app.kb_chunks` (via
`app/glossary/embed.py`/`verify_embed.py`, mirroring `app/catalog/embed.py`'s exact
convention), `retrieve_relevant_glossary_entries()` + `build_glossary_context()` in
`generate_sql.py`, a `$glossary_context` section in `prompts/generate_sql.md`, and
threads the new context through `build_prompt()`/`call_llm_for_sql()`/`generate_sql()`.
Eval re-run confirms no regression (5/5, run fresh 4 times this session). Matches the
goal exactly.

Disclosed extras (all direct, necessary fallout of doubling `generate_sql()`'s Voyage
calls per question — not scope creep):
- `RATE_LIMIT_MAX_ATTEMPTS` 4→6 in `app/catalog/embed.py` (real `RateLimitError`
  exhaustion observed this slice).
- `stop_verify.py` timeout 1200s→2400s; `tests/_answer_helpers.py` /
  `tests/_generate_sql_helpers.py` timeouts 120s→450s (real observed runtimes exceeded
  the old ceilings).
- `CLAUDE.md`'s documented test runtime bumped ~15min→~30min to match reality.
- `tests/test_describe_cli.py`'s `kb_chunks`-nonexistence test retargeted to a real
  behavioral check, because the brief itself invalidates the old premise (this slice
  legitimately creates `app.kb_chunks`).
- `tests/test_generate_sql_prompt_file.py`'s pre-existing substitutability test updated
  to supply `glossary_context`, because the prompt template gained a new required
  placeholder this slice.

**PASS.**

## 3. The eval or test passed

Eval (run fresh, final state):
```
$ python -m evals.run
[PASS] What are the top 5 product categories by number of orders?
[PASS] Which payment type is used the most, by number of payments?
[PASS] Which customer state has the most customers?
[PASS] How many orders have the status 'delivered'?
[PASS] What is the average review score across all reviews?
5/5 correct
```
Stable across 4 separate runs this session (after fixing a real mid-slice regression —
see "Rejected or changed" below).

Full suite (run fresh, final state):
```
$ python -m unittest discover tests
............................................................................................................................................................................
----------------------------------------------------------------------
Ran 172 tests in 230.491s

OK
```
Clean on 2 of 7 attempts this session. The other 5 hit either the pre-existing,
HANDOFF-documented Stop-hook/shared-DB-row concurrency hazard (unrelated to this slice's
code; confirmed via a real Postgres deadlock in `test_seed_idempotency.py`, an M1-era
test with zero connection to this diff) or a genuine Voyage rate-limit exhaustion (now
fixed, see check 2's disclosed extras). User explicitly chose "one more full-suite
attempt" after reviewing this evidence; that attempt is the clean run pasted above.

**PASS.**

## 4. The no-slop review found no unresolved issues

First pass (mid-slice) found 4 real findings:
1. `retrieve_relevant_tables()`/`retrieve_relevant_glossary_entries()` each
   independently embed the same question (doubled Voyage call) with no comment naming
   it as a deliberate tradeoff. **Fixed**: inline comment added in `generate_sql()`.
2. `tests/test_describe_cli.py`'s `kb_chunks` check was a weak source-text-grep proxy
   instead of real behavior. **Fixed**: rewritten as a real before/after
   existence-and-row-count check across a `describe.py` re-run.
3. `GLOSSARY_RETRIEVAL_K = 3` had no rationale comment. **Fixed**: one-line comment
   added.
4. `EMBEDDING_DIMENSION` imported into `app/glossary/embed.py` but never used in its own
   body. **Fixed**: `SCHEMA_DDL` is now an f-string that actually interpolates it,
   removing the hardcoded-literal duplication too.

Second pass (final diff, independent re-verification of all 4 fixes plus a full fresh
10-category walk): zero findings.

**PASS.**

## 5. The shipping proof is attached

Ran a fresh question never in the eval set, live, to prove glossary retrieval genuinely
changes generation (not just passing 5 curated questions):
```
$ python -c "... retrieve_relevant_glossary_entries(cur, vc, 'What is the average order value?') ..."
Retrieved glossary entries for: 'What is the average order value?'
 - average-order-value-aov
 - average-items-per-order
 - average-payment-installments

Generated SQL:
SELECT SUM(price) / COUNT(DISTINCT order_id) AS average_order_value FROM olist.order_items
```
Executed against the real DB:
```
Real AOV result: (Decimal('137.7540763788944520'),)
```
The AOV KPI was correctly retrieved (top hit) and the generated SQL matches its glossary
formula exactly, producing a real, sane result.

**PASS.**

## Rejected or changed

**A real regression was caught and fixed mid-slice**, not just a style nit: the first
version of `glossary.md`'s "Top Product Category" and "Repeat Purchase Rate" KPI entries
were too prescriptive and leaked into unrelated questions — steering the LLM to use
`COUNT(*)` with translated category names (instead of `COUNT(DISTINCT order_id)` with
the untranslated name the eval's ground truth uses) and to always group customers by
`customer_unique_id` even for a plain "count customers by state" question. This dropped
the eval from 5/5 to 3/5. Diagnosed by comparing generated SQL against direct DB queries,
rewrote both entries to explicitly scope their guidance, deleted and re-embedded the two
affected `app.kb_chunks` rows, and reconfirmed 5/5 twice.

Separately, per the no-slop review: fixed the 4 findings listed in check 4 rather than
shipping them silently.

## Verdict

**Accept** — all five checks pass. User reviewed this summary (goal match, fresh
tests/eval, no-slop resolution, shipping proof, and the mid-slice regression/fix) and
explicitly chose Accept.
