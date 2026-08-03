# Review gate — repair-loop

Date: 2026-08-03
Brief: plans/briefs/2026-08-03-repair-loop.md
Diff reviewed: working tree (pre-commit), 7 files (5 new, 1 modified,
plus the auto-capture log), 722 insertions(+), 8 deletions(-)

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review
```
app/pipeline/answer.py                 |  52 ++++++-
app/pipeline/repair_sql.py             |  50 +++++++
evals/repair_sql.md                    |  63 ++++++++
plans/briefs/2026-08-03-repair-loop.md |  94 ++++++++++++
prompts/repair_sql.md                  |  28 ++++
tests/test_answer_repair.py            | 265 +++++++++++++++++++++++++++++++++
tests/test_repair_sql.py               | 178 ++++++++++++++++++++++
7 files changed, 722 insertions(+), 8 deletions(-)
```
Core implementation is two small files (`repair_sql.py`, ~55 lines of new
logic in `answer.py`'s refactor, including the `_retry_once()` extraction
added at the human reviewer's request — see Check 4); the rest is a new
prompt, a new eval doc, the brief, and two test files. Every file is
single-purpose and short. Read line by line. PASS.

(`plans/logs/_auto-capture.md` also shows modified — that's the
capture_commit hook's trailing append from the *previous* slice's commit,
not part of this diff.)

## 2. The stated goal matches the actual change
Brief's Goal: when generated SQL fails `validate_sql()` or the real DB
execute in `get_answer()`, automatically retry exactly once via a new
`repair_sql()` call (question + failed SQL + real error) before giving
up — closing out M3.

What the diff does: adds `prompts/repair_sql.md` (new, versioned,
`string.Template`, 3 placeholders — `$question`/`$failed_sql`/`$error`);
adds `app/pipeline/repair_sql.py` (`repair_sql(question, failed_sql,
error_message)`, one Anthropic call, no internal retry, reusing
`GenerateSqlResponse`/`DEFAULT_MODEL` from `generate_sql.py`); refactors
`app/pipeline/answer.py` into `_validate_and_execute(sql)` +
`_retry_once(attempt, recover)` (a pure, I/O-free control-flow helper:
try `attempt()`, on any exception call `recover(exc)` once, let a second
failure propagate unmodified) + `_answer_with_repair(question, sql)`
(binds `_retry_once` to the real `_validate_and_execute`/`repair_sql`
calls) + `get_answer()` (now `generate_sql()` then
`_answer_with_repair()`); adds `evals/repair_sql.md` (2 real cases, one
per trigger path) and two new test files proving the mechanism fires for
real.

Confirmed via `git diff` that `generate_sql.py` (retrieval/generation),
`validate_sql.py`, and `execute_sql.py` are byte-identical to the prior
commit — no scope creep into upstream modules. No FastAPI/frontend
changes, no CI changes, no more-than-one-repair-attempt, no touch to the
known concurrency hazard. Goal and diff match. PASS.

## 3. The eval or test passed
Dedicated repair-path tests, run fresh, standalone:
```
$ ./.venv/Scripts/python -m unittest discover -s tests -p "test_repair_sql.py" -v
test_repair_sql_output_passes_a_fresh_real_validate_sql_call ... ok
test_repair_sql_returns_a_different_sql_string_than_the_broken_input ... ok
test_repair_sql_returns_a_nonblank_string ... ok
test_the_handcrafted_sql_really_does_fail_real_column_validation ... ok
test_repair_sql_prompt_file_exists_and_is_non_blank ... ok
test_repair_sql_has_the_gate_1_signature ... ok
----------------------------------------------------------------------
Ran 6 tests in 19.535s
OK

$ ./.venv/Scripts/python -m unittest discover -s tests -p "test_answer_repair.py" -v
test_answer_with_repair_does_not_raise_for_the_handcrafted_broken_sql ... ok
test_answer_with_repair_returns_a_different_sql_than_the_broken_input ... ok
test_answer_with_repair_returns_a_select_statement ... ok
test_answer_with_repair_returns_a_sql_and_rows_pair ... ok
test_answer_with_repair_returns_real_nonempty_rows ... ok
test_answer_with_repair_delegates_to_retry_once ... ok
test_answer_with_repair_is_an_async_function_of_question_and_sql ... ok
test_get_answer_actually_calls_answer_with_repair ... ok
test_retry_once_calls_recover_with_the_first_exception_and_returns_its_result ... ok
test_retry_once_never_calls_recover_before_attempt_fails ... ok
test_retry_once_propagates_a_second_failure_unmodified ... ok
test_retry_once_returns_the_first_attempts_result_when_it_succeeds ... ok
----------------------------------------------------------------------
Ran 12 tests in 4.178s
OK
```
The last four (`RetryOnceTests`) were added after the human reviewer asked
for the "second failure propagates unmodified" claim to be actually
proven rather than left as a written exception — see Check 4.
`test_retry_once_propagates_a_second_failure_unmodified` is the direct
proof: `recover()` raising a distinct `RuntimeError` surfaces from
`_retry_once()` as that exact exception object, unmodified.

Eval regression check:
```
$ ./.venv/Scripts/python -m evals.run
[PASS] What are the top 5 product categories by number of orders?
[PASS] Which payment type is used the most, by number of payments?
[PASS] Which customer state has the most customers?
[PASS] How many orders have the status 'delivered'?
[PASS] What is the average review score across all reviews?
[PASS] What is the average order value?
6/6 correct
```

Full suite, run fresh, solo (no other test invocation running
concurrently, foreground/blocking so nothing overlapped with the
automatic Stop-hook run at turn end):
```
$ ./.venv/Scripts/python -m unittest discover tests
..............................................................................................................................................................................................
----------------------------------------------------------------------
Ran 190 tests in 203.893s
OK
```
190 = prior 185 + 5 new (`RetryOnceTests`'s 4 tests +
`test_answer_with_repair_delegates_to_retry_once`). PASS.

**Incident during this gate, not a regression from this slice:** an
earlier full-suite attempt failed with
`test_glossary_verify_embed.py::test_verify_embed_exits_zero_against_an_embedded_glossary`
reporting `app.kb_chunks` missing the `active-seller-count` row — the
exact pre-existing Stop-hook/shared-mutable-DB-row hazard HANDOFF.md
already documents (a mutate-restore-in-`finally` test's restore raced
against a concurrent run and lost). Root cause this time: the harness's
Stop hook (`.claude/hooks/stop_verify.py`) runs its own full
`unittest discover tests` automatically at every turn boundary,
independent of anything run manually — several `run_in_background: true`
full-suite invocations in this session were still executing when a turn
ended, so the hook's own run raced them on that shared row. Repaired per
HANDOFF's documented recipe (`python -m app.glossary.embed`, which only
re-embeds sources not already present — confirmed via
`python -m app.glossary.verify_embed` showing all 16 `[OK]` immediately
after), then re-ran the full suite solo/foreground (above) to get a
clean, non-racing result. No test logic was touched. Not this slice's
bug — flagging it here per CLAUDE.md/HANDOFF's own convention for this
recurring hazard, and noting for future sessions: prefer a single
foreground full-suite run over `run_in_background`, since a background
run left executing across a turn boundary is exactly what races the
automatic Stop hook.

## 4. The no-slop review found no unresolved issues
no-slop-reviewer subagent (read-only) ran twice — once against the first
draft, once against the final diff after fixes.

Round 1 findings, both fixed before round 2:
1. **[category 8, scope]** `prompts/repair_sql.md` had no matching
   `evals/*.md` case — `templates/no-slop.md` item 8 requires one for
   every new/changed prompt file (previously caught on the generate-sql
   slice). Fixed: added `evals/repair_sql.md` with two real cases (one
   triggering repair via a `validate_sql()` failure, one via a real
   `execute_sql()` failure), both run for real and pasted with actual
   output.
2. **[category 2/7, minor]** `call_llm_for_repair()`'s final-failure path
   let a raw `json.JSONDecodeError`/`ValidationError` propagate unwrapped,
   diverging from `generate_sql.py`'s sibling convention of a clear,
   actionable message. Fixed: now wraps it in
   `RuntimeError(f"LLM failed to produce a valid repaired SELECT
   statement: {exc}")`.
3. **[category 3, low-severity note, not a required fix]**
   `call_llm_for_repair()` structurally echoes `call_llm_for_sql()`
   (prompt build → Anthropic call → parse → validate). Only 2
   occurrences (rubric's bar is 3) — not extracted, noted only.

Round 2 (final diff): both fixes verified as correctly applied; no new
blocking findings. One judgment-call item was surfaced to the user rather
than silently decided: the brief's "second failure propagates unmodified"
path had no dedicated test proving a *second* failure actually surfaces,
because constructing a guaranteed double-failure deterministically
appeared to require mocking `repair_sql()`'s output — against this
project's no-mock convention.

**User pushed back and asked for this to actually be fixed, not carried
as a written exception.** Resolution: extracted the try/repair-once/
propagate shape into a new `_retry_once(attempt, recover)` helper that
has no I/O of its own (no DB, no LLM) — `_answer_with_repair` now binds
it to the real `_validate_and_execute`/`repair_sql` calls via two small
closures. Because `_retry_once` itself performs no I/O, its propagation
semantics are testable with plain, real Python functions standing in for
`attempt`/`recover` — not mocks of any real dependency, since there's no
dependency to mock at that layer. `RetryOnceTests` (`tests/
test_answer_repair.py`) now proves, deterministically: attempt-succeeds
returns its result without calling recover; attempt-fails calls recover
with the exact exception; **recover-also-fails propagates that second
exception, unmodified, as the exact same object** (the brief's precise
claim); recover only ever runs after attempt fails. `_answer_with_repair`
keeps its exact Gate-1-approved signature and behavior — only its
internal implementation changed, confirmed unbroken by the pre-existing
`AnswerWithRepairEndToEndTests`/`AnswerWithRepairSignatureTests` classes
still passing unchanged.

All other categories (dead code, duplication, naming, comments,
consistency, fake done, verified-not-claimed) reported clean in both
rounds. No unresolved findings remain. PASS.

## 5. The shipping proof is attached
Real CLI run, fresh, this session — proves the unchanged happy path still
works end to end through the refactored `get_answer()`:
```
$ ./.venv/Scripts/python -m app.pipeline.verify_answer
SQL:
SELECT p.product_category_name, COUNT(DISTINCT oi.order_id) AS order_count FROM olist.order_items oi JOIN olist.products p ON oi.product_id = p.product_id GROUP BY p.product_category_name ORDER BY order_count DESC LIMIT 5

Rows:
{'product_category_name': 'cama_mesa_banho', 'order_count': 9417}
{'product_category_name': 'beleza_saude', 'order_count': 8836}
{'product_category_name': 'esporte_lazer', 'order_count': 7720}
{'product_category_name': 'informatica_acessorios', 'order_count': 6689}
{'product_category_name': 'moveis_decoracao', 'order_count': 6449}

verify_answer: PASSED
```
Separately (not asserted, demonstrated live): the new repair path itself
was exercised for real, outside the committed test suite, once per
trigger — a `validate_sql()`-rejected SQL (`SELECT
nonexistent_column_xyz FROM olist.orders`) repaired for real into
`SELECT COUNT(*) FROM olist.orders`, and a real `execute_sql()` failure
(`SELECT price / (price - price) ... division by zero`) repaired into
`SELECT AVG(price) / AVG(price) ...`, which executed and returned real
rows. Both are documented with full input/output in `evals/repair_sql.md`.
PASS.

## Rejected or changed
Three things changed from the first draft, none rubber-stamped: added
`evals/repair_sql.md` (the prompt would otherwise have shipped with zero
eval coverage — the exact pattern CLAUDE.md's standing rule and the
no-slop rubric both name as previously caught, found by the no-slop
pass); wrapped `call_llm_for_repair()`'s final failure in an informative
`RuntimeError` instead of a raw library exception (no-slop pass); and,
at the user's explicit request, replaced the accepted-exception around
the untested "second failure propagates" path with an actual
deterministic test, via the `_retry_once()` extraction described in
Check 4 — the user rejected "documented exception" as good enough and
asked for a real fix, which is exactly what this record now shows.

## Verdict
accept — all five checks green.
