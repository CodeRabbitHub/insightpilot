# Handoff

Date: 2026-08-03
Slice just completed: plans/briefs/2026-08-03-repair-loop.md +
  plans/logs/2026-08-03-repair-loop.md (commit ba76f79)

## State of the work
- **`get_answer()` now self-corrects once via a new one-shot repair
  loop, closing out M3 entirely** (retrieval + repair + evals). New
  `app/pipeline/repair_sql.py`'s `repair_sql(question, failed_sql,
  error_message)` makes one Anthropic call (no internal retry --
  PRD F2's "max 2 attempts total" budgets exactly one generate + one
  repair call) against a new, versioned `prompts/repair_sql.md`
  (`string.Template`, 3 placeholders: `$question`/`$failed_sql`/`$error`),
  reusing the existing `GenerateSqlResponse` Pydantic model and
  `DEFAULT_MODEL` from `generate_sql.py` -- no new provider, no new
  response schema.
- **`app/pipeline/answer.py` was refactored into three layers**:
  `_validate_and_execute(sql)` (the original validate-then-execute
  chain, unchanged in behavior), a new `_retry_once(attempt, recover)`
  (a pure, I/O-free control-flow helper -- try `attempt()`, on any
  exception call `recover(exc)` once, let a second failure propagate
  unmodified), and `_answer_with_repair(question, sql)` (binds
  `_retry_once` to the real `_validate_and_execute`/`repair_sql` calls).
  `get_answer()` is now just `generate_sql()` then
  `_answer_with_repair()`.
- **The "second failure propagates unmodified" claim (PRD F2's exact
  wording) is proven deterministically, with zero mocking** -- this was
  a genuine mid-gate correction. The first gate draft left it as a
  written exception (reasoning that forcing a guaranteed double-failure
  would need mocking `repair_sql()`'s output, against this project's
  no-mock convention). Directly instructed to fix it rather than accept
  the exception: extracting `_retry_once()` gave the propagation
  semantics zero I/O of their own, so `RetryOnceTests`
  (`tests/test_answer_repair.py`) proves them with plain, real Python
  functions standing in for `attempt`/`recover` -- not mocks of any real
  dependency, since there's nothing to mock at that layer. Lesson
  worth carrying forward: "can't test this without mocking" is often
  "haven't found the seam yet," not a genuine dead end.
- **A new `evals/repair_sql.md` gives the new prompt real eval
  coverage** -- `evals/questions.yaml`'s 6/6 never exercises
  `repair_sql.md` at all (every question succeeds on the first
  `generate_sql()` try), so this was a real gap the no-slop-reviewer
  subagent caught (matching the exact pattern from the generate-sql
  slice: "a prompt change without an eval run is not done"). Two real
  cases, one per way `_answer_with_repair()` can trigger repair: a
  `validate_sql()` rejection (`SELECT nonexistent_column_xyz FROM
  olist.orders` -> repaired to `SELECT COUNT(*) FROM olist.orders`) and
  a real `execute_sql()` failure (`SELECT price / (price - price) ...`
  -> division by zero -> repaired to `SELECT AVG(price) / AVG(price)
  ...`, which executed and returned real rows).
- Both done-checks pass fresh, most recent run:
  ```
  $ python -m unittest discover -s tests -p "test_repair_sql.py" -v
  Ran 6 tests in 19.535s
  OK

  $ python -m unittest discover -s tests -p "test_answer_repair.py" -v
  Ran 12 tests in 4.178s
  OK

  $ python -m evals.run
  [PASS] What are the top 5 product categories by number of orders?
  [PASS] Which payment type is used the most, by number of payments?
  [PASS] Which customer state has the most customers?
  [PASS] How many orders have the status 'delivered'?
  [PASS] What is the average review score across all reviews?
  [PASS] What is the average order value?
  6/6 correct

  $ python -m unittest discover tests
  Ran 190 tests in 203.893s
  OK
  ```
- Real, live shipping proof beyond the curated eval questions:
  `python -m app.pipeline.verify_answer` PASSED (unchanged happy path
  through the refactored `get_answer()`), plus the two live repair-path
  demonstrations documented above with full input/output in
  `evals/repair_sql.md`.

## Proof
See the four command blocks above (`test_repair_sql`, `test_answer_repair`,
`evals.run`, `unittest discover tests`). All run fresh, standalone, this
session, on the final committed state (`ba76f79`).

## Open questions / known issues
- **The Stop-hook/shared-DB-row concurrency hazard is now this
  session's dedicated next slice -- root cause is precisely diagnosed
  for the first time.** `.claude/hooks/stop_verify.py` runs a full
  `python -m unittest discover tests` automatically every time the
  agent's turn ends, completely independent of anything run manually.
  Any full-suite invocation (manual, or a stray `run_in_background:
  true` one still executing across a turn boundary) can therefore
  overlap with the hook's own automatic run against the *same live
  Postgres database*. Two specific tests are structurally guaranteed to
  race when that overlap lands during their execution window, because
  each does a REAL, committed mutation of a shared row (not a
  transaction rollback) so a subprocess it shells out to can observe
  the change:
  - `tests/test_verify_describe_script.py:73-109`
    (`test_verify_describe_fails_when_a_description_is_missing`) --
    `SELECT ... ORDER BY table_name LIMIT 1` (always picks `customers`,
    alphabetically first), sets its `app.catalog_tables.description` to
    `NULL`, shells out to `python -m app.catalog.verify_describe`
    (a fresh connection, so it must see a *committed* change), asserts
    non-zero exit, restores the original description in `finally`.
  - `tests/test_glossary_verify_embed.py:66-104`
    (`test_verify_embed_fails_when_a_kb_chunk_is_missing`) -- same
    shape: `SELECT ... ORDER BY source LIMIT 1` (always picks
    `active-seller-count`), `DELETE`s that `app.kb_chunks` row, shells
    out to `python -m app.glossary.verify_embed`, asserts non-zero
    exit, re-`INSERT`s the original row in `finally`.
  - `tests/test_seed_idempotency.py` hit a genuine Postgres deadlock
    this session too -- an M1-era test with zero connection to this
    slice's code, but direct proof two full-suite invocations
    genuinely overlapped in time.

  Recurred across 3 consecutive sessions now (first logged in the
  eval-harness-v1 handoff, recurred in glossary-retrieval, recurred
  again this session) -- well past the ratchet's "2nd repetition ->
  promote" threshold. **Per direct sign-off, this is the next slice**
  (brief below), not another deferral. If it recurs again before then:
  repair the specific row (`UPDATE app.catalog_tables SET description =
  NULL` + `python -m app.catalog.describe` for `customers`;
  `python -m app.glossary.embed` after deleting the affected
  `app.kb_chunks` row if one goes missing -- `embed()` only re-embeds
  sources not already present, so it's always safe to re-run) rather
  than touching test logic. Practical mitigation in the meantime: prefer
  a single foreground (blocking) full-suite run over
  `run_in_background`, since a background run still executing across a
  turn boundary is exactly what races the automatic Stop hook.
- The doubled-Voyage-call-per-question design cost (schema + glossary
  each independently embed the same question text) remains unoptimized
  -- accepted, documented in code (`app/pipeline/generate_sql.py`'s
  `generate_sql()`), not a blocker.
- Lint/type tooling (`ruff`, `mypy`) and the test runner (`unittest`, not
  `pytest`) remain unaddressed, carried over from every prior slice --
  still not blocking.

## Next slice (the brief, written NOW while context is hot)
Goal:
Make the two structurally-racy tests (`test_verify_describe_script.py`'s
`test_verify_describe_fails_when_a_description_is_missing` and
`test_glossary_verify_embed.py`'s
`test_verify_embed_fails_when_a_kb_chunk_is_missing`) safe under
concurrent full-suite invocation, so the Stop-hook/shared-DB-row hazard
(3 consecutive sessions now) stops recurring.

Constraints:
Python 3.12, existing `psycopg2`-based connections
(`app.catalog.sync.connect()`); no new dependency without asking first
(CLAUDE.md). Both tests must keep proving what they prove today --
a real subprocess invocation of the actual CLI (`verify_describe`/
`verify_embed`) genuinely catching a real missing/NULL row, not a
mocked or weakened assertion (never weaken a test to make it pass, per
CLAUDE.md). The fix must hold even though each test's mutation has to
be a real, committed database change (the CLI it shells out to opens
its own connection, so an uncommitted/rolled-back change would be
invisible to it -- a plain transaction-rollback fix does not work
here). The leading candidate (confirm or replace at Gate 1): a Postgres
session-scoped advisory lock (`pg_advisory_lock`/`pg_advisory_unlock`
-- built into Postgres, no new dependency) taken around each test's
delete/null-mutate -> subprocess-check -> restore window, so two
concurrent invocations of the *same* racy test serialize against each
other instead of racing. `tests/test_seed_idempotency.py`'s deadlock is
supporting evidence of overlap, not itself in scope to fix (M1-era,
unrelated code).

Inputs:
`tests/test_verify_describe_script.py:73-109`,
`tests/test_glossary_verify_embed.py:66-104` (the two racy tests, exact
line ranges above); `.claude/hooks/stop_verify.py` (confirms the
automatic-every-turn root cause); `app/catalog/sync.py` (`connect()`,
the shared psycopg2 connection helper both tests already use);
this handoff's Open Questions section above (full root-cause diagnosis,
done this session -- don't re-derive it).

Outputs:
Both tests made safe under real concurrent execution (via advisory
locking, or a Gate-1-confirmed alternative); a new, dedicated
concurrency-proof script (e.g. `tests/verify_concurrency_safety.py` or
similar, mirroring this project's existing `verify_*` CLI convention)
that deliberately launches multiple concurrent subprocess invocations of
these two test files and asserts every invocation exits 0 -- proving
the fix under genuine concurrent load, not just "no flake observed this
run."

Done-check:
The new concurrency-proof script exits 0, run fresh, output pasted --
e.g. `python -m tests.verify_concurrency_safety` (exact command/module
name confirmed at Gate 1) launching at least 2 concurrent runs of both
racy test files and reporting every run passed. Separately,
`python -m unittest discover tests` still passes in full (paste output;
expect ~20-30 min real runtime per CLAUDE.md -- not hung).

Out-of-scope:
`tests/test_seed_idempotency.py`'s own deadlock (M1-era, unrelated
code -- supporting evidence only); any other test file beyond the two
named above, even if a similar pattern is spotted (flag it, don't fix
it silently -- separate slice); FastAPI/frontend (M4, starts after this
lands); the doubled-Voyage-call design cost; lint/type tooling.
