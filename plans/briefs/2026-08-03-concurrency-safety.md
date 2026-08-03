# Brief — concurrency-safety

Date: 2026-08-03
Milestone: N/A — cross-cutting test-infra fix (recurring hazard, not a
  PLAN.md milestone item); lands before M4 kickoff so the Stop hook stops
  racing manual full-suite runs.

Goal:
Make `test_verify_describe_script.py`'s
`test_verify_describe_fails_when_a_description_is_missing` and
`test_glossary_verify_embed.py`'s
`test_verify_embed_fails_when_a_kb_chunk_is_missing` safe under two
concurrent full-suite invocations hitting the same live Postgres
database, so the Stop-hook/shared-DB-row race (recurred 3 consecutive
sessions) stops corrupting rows.

Constraints:
- Python 3.12, existing `psycopg2` connections
  (`app.catalog.sync.connect()` / `tests._pg_helpers.get_admin_connection()`)
  — no new dependency without asking first (CLAUDE.md).
- Fix must use a Postgres session-scoped advisory lock
  (`pg_advisory_lock`/`pg_advisory_unlock` — built into Postgres, zero new
  dependency) taken around each test's mutate → subprocess-check → restore
  window, so two concurrent invocations of the *same* racy test serialize
  instead of racing. Confirm the exact lock key scheme at Gate 1 (e.g. one
  fixed bigint key per test file, via `hashtext('<stable-string>')`).
- Both mutations must stay real, committed DB changes (`autocommit = True`,
  as today) — the CLI each test shells out to (`verify_describe`/
  `verify_embed`) opens its own connection and must observe a committed
  row, so a transaction-rollback-based fix does not work here.
- Never weaken, skip, or delete a test to make it pass (CLAUDE.md) — both
  tests must keep proving exactly what they prove today: a real subprocess
  invocation of the real CLI genuinely catching a real missing/NULL row.
- Do not change `verify_describe.py`/`verify_embed.py`'s own validation
  logic — only add locking around the two tests' mutation windows.

Inputs:
- `tests/test_verify_describe_script.py:73-109`
  (`test_verify_describe_fails_when_a_description_is_missing`) and
  `tests/test_glossary_verify_embed.py:66-104`
  (`test_verify_embed_fails_when_a_kb_chunk_is_missing`) — the two racy
  tests, exact current bodies.
- `.claude/hooks/stop_verify.py` — confirms the automatic-every-turn root
  cause (a full `unittest discover tests` run on every Stop, independent of
  any manual run).
- `tests/_pg_helpers.py` (`get_admin_connection()`, `conn_params()`) and
  `app/catalog/sync.py` (`connect()`) — the existing psycopg2 connection
  helpers both tests already use; no new connection abstraction needed.
- HANDOFF.md's "Open questions / known issues" section (full root-cause
  diagnosis, already done — don't re-derive it).

Outputs:
- Both racy tests wrap their mutate → subprocess-check → restore window in
  a session-scoped `pg_advisory_lock`/`pg_advisory_unlock` pair (or
  `finally`-guarded equivalent) keyed so concurrent runs of the *same* test
  serialize.
- A new concurrency-proof script (`tests/verify_concurrency_safety.py` or
  similar, mirroring the project's existing `verify_*` CLI convention) that
  launches at least 2 concurrent subprocess invocations of both racy test
  files and asserts every invocation exits 0 — proving the fix under real
  concurrent load, not "no flake observed this run."

Done-check:
Both, pasted, fresh, in one sitting:
1. `python -m tests.verify_concurrency_safety` (exact module name confirmed
   at Gate 1) exits 0, launching ≥2 concurrent runs of both racy test files
   and reporting every run passed.
2. `python -m unittest discover tests` passes in full (expect ~5-10 min
   real runtime per CLAUDE.md — not hung).

Out-of-scope:
- `tests/test_seed_idempotency.py`'s own deadlock (M1-era, unrelated code —
  supporting evidence only that overlap happens, not itself fixed here).
- Any other test file, even if a similar shared-row pattern is spotted —
  flag it, don't fix it silently; separate slice.
- FastAPI/frontend (M4, starts after this lands).
- The doubled-Voyage-call-per-question design cost.
- Lint/type tooling (`ruff`, `mypy`), switching `unittest` to `pytest`.
