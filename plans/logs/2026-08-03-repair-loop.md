# Slice log — repair-loop

Date: 2026-08-03
Brief: plans/briefs/2026-08-03-repair-loop.md

## The plan you approved
New `app/pipeline/repair_sql.py` (one file per pipeline step, mirroring
`generate_sql.py`/`validate_sql.py`/`execute_sql.py`), reusing
`GenerateSqlResponse`/`DEFAULT_MODEL`. `answer.py` gains an internal
`_answer_with_repair(question, sql)` seam — the exact function
`get_answer()` calls after `generate_sql()` returns — tested directly
with a hand-crafted broken SQL string instead of relying on the LLM
failing on its own, so the repair path could be proven with zero mocking.

## The diff you accepted
Commit `ba76f79` — "One-shot SQL repair loop: get_answer() self-corrects
on validate/execute failure." 8 files changed, 961 insertions(+), 8
deletions(-): `app/pipeline/repair_sql.py` (new), `prompts/repair_sql.md`
(new), `app/pipeline/answer.py` (refactored into
`_validate_and_execute()` / `_retry_once()` / `_answer_with_repair()` /
`get_answer()`), `evals/repair_sql.md` (new), `tests/test_repair_sql.py`
+ `tests/test_answer_repair.py` (new, 19 tests total), plus the approved
brief and gate record. Full mechanics: `plans/logs/_auto-capture.md`.
Full detail: `artifacts/reviews/2026-08-03-repair-loop.md`.

## The done-check output
```
$ ./.venv/Scripts/python -m unittest discover -s tests -p "test_repair_sql.py" -v
Ran 6 tests in 19.535s
OK

$ ./.venv/Scripts/python -m unittest discover -s tests -p "test_answer_repair.py" -v
Ran 12 tests in 4.178s
OK

$ ./.venv/Scripts/python -m evals.run
[PASS] What are the top 5 product categories by number of orders?
[PASS] Which payment type is used the most, by number of payments?
[PASS] Which customer state has the most customers?
[PASS] How many orders have the status 'delivered'?
[PASS] What is the average review score across all reviews?
[PASS] What is the average order value?
6/6 correct

$ ./.venv/Scripts/python -m unittest discover tests
Ran 190 tests in 203.893s
OK
```
190 = prior 172 + 19 new (`plans/briefs/2026-08-03-repair-loop.md`'s two
test files). All four run fresh, standalone, this session, on the final
committed state. Full paste with context: `artifacts/reviews/
2026-08-03-repair-loop.md`.

## One thing you rejected or changed
Rejected the documented-exception approach for the untested
second-failure-propagation path; required an actual deterministic test.
The first gate draft left "a second failure propagates unmodified"
(PRD F2's exact wording) as a written exception rather than a test,
reasoning that forcing a guaranteed double-failure would need mocking
`repair_sql()`'s output — against this project's no-mock convention.
Pushed back on that: the fix was to extract the try/repair-once/
propagate shape into a new `_retry_once(attempt, recover)` helper with
no I/O of its own, so its propagation semantics could be proven with
plain, real Python functions (not mocks of any real dependency, since
there's nothing to mock at that layer) — `RetryOnceTests` now proves it
directly, including the exact "recover also fails -> that failure
surfaces unmodified" claim. `_answer_with_repair`'s public signature and
behavior were unchanged by this; only its internal implementation moved
one level down. Lesson for future gates: "can't test this without
mocking" is often really "haven't found the seam yet," not a genuine
dead end — worth one more pass at extraction before accepting the
exception.

Separately, not part of this slice's own work but hit mid-gate: the
pre-existing Stop-hook/shared-DB-row concurrency hazard (first logged in
the eval-harness-v1 handoff, recurred in glossary-retrieval) recurred a
third consecutive session. Root cause is now understood precisely for
the first time: `.claude/hooks/stop_verify.py` runs its own full
`unittest discover tests` automatically at every turn boundary,
independent of anything run manually — a `run_in_background: true`
full-suite invocation left executing across a turn boundary races the
hook's own automatic run on `app.kb_chunks`. Repaired the specific row
(`python -m app.glossary.embed`) and re-verified clean with a solo,
foreground run; no test logic touched.

## The next smallest slice
Per direct sign-off: with M3 now fully closed and this hazard confirmed
recurring for a third consecutive session (the ratchet's own "2nd
repetition -> promote" threshold long since passed — HANDOFF.md already
called it "overdue"), the next slice is dedicated to actually fixing the
Stop-hook/shared-DB-row concurrency hazard — giving the mutate-restore
tests (`test_glossary_verify_embed.py`, the pre-existing `customers`-
description one, `test_seed_idempotency.py`) their own isolated row, or
adding a `stop_verify` lock file so two full-suite invocations can't
overlap in the first place — before M4 (FastAPI) starts.
