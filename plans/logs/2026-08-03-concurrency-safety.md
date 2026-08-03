# Slice log — concurrency-safety

Date: 2026-08-04
Brief: plans/briefs/2026-08-03-concurrency-safety.md

## The plan you approved
A session-scoped Postgres advisory lock (`pg_advisory_lock(hashtext(key))`,
not `pg_advisory_xact_lock` — both tests run with `autocommit = True`, so
an xact-scoped lock would release before the subprocess check could run),
wrapping each racy test method's own mutate → check → restore window, plus
a new `tests/verify_concurrency_safety.py` launching real concurrent
subprocess invocations of both racy test files to prove it.

## The diff you accepted
Commit `534ed01` — "Serialize the two racy verify tests against
concurrent full-suite runs." 6 files changed, 349 insertions(+), 15
deletions(-): `tests/_pg_helpers.py` (new `acquire_advisory_lock()` /
`release_advisory_lock()`), `tests/test_verify_describe_script.py` +
`tests/test_glossary_verify_embed.py` (lock now taken in `setUpClass`,
released via `addClassCleanup`), `tests/verify_concurrency_safety.py`
(new), plus the approved brief and gate record. Full mechanics:
`plans/logs/_auto-capture.md`. Full detail: `artifacts/reviews/
2026-08-03-concurrency-safety.md` — which also records five full
no-slop-reviewer passes, not one, because the design changed twice
after the first pass (see below).

## The done-check output
```
$ python -m tests.verify_concurrency_safety
  [OK] test_verify_describe_script.py (run 0): exit=0
  [OK] test_verify_describe_script.py (run 1): exit=0
  [OK] test_glossary_verify_embed.py (run 0): exit=0
  [OK] test_glossary_verify_embed.py (run 1): exit=0

verify_concurrency_safety: PASSED

$ python -m unittest discover tests
Ran 190 tests in 221.133s

OK
```
Both re-run 3+ times across the session's design iterations, always
consistent. Full paste with context: `artifacts/reviews/
2026-08-03-concurrency-safety.md`.

## One thing you rejected or changed
Rejected the first accepted design outright, even though it had already
passed its own concurrency proof and a clean no-slop review: locking all
3 test methods per file (6 total, via a per-method `with advisory_lock():`
wrapper), when the brief's Constraints named only the 2 specific racy
tests. The narrower, brief-literal version (lock only the 2 named tests)
had genuinely failed the concurrency proof first — the other, read-only
tests in the same classes assume a clean catalog/glossary and can observe
a concurrent process's mid-mutation state — so expanding to all 3 methods
was the fix that actually worked. Direct instruction was still to not
accept that shape: move the lock to `setUpClass`/`tearDownClass` instead,
serializing the whole class's run once instead of threading it through
every method body.

That rejection is what surfaced two further, genuine bugs that the
broader per-method version had incidentally papered over:
1. `setUpClass` called `run_describe()`/`run_glossary_embed()` *before*
   acquiring the lock — both silently "heal" any NULL/missing row they
   find, so a concurrent process's own unlocked setup could undo another
   process's in-progress mutation before that process ever checked it.
   Fixed by acquiring the lock first.
2. `tearDownClass` never runs if `setUpClass` raises (real, reachable: the
   describe/embed calls carry real subprocess timeouts) — leaking the
   session-scoped lock and connection for the rest of that process's
   life, exactly the stall this slice exists to prevent. Fixed by
   `addClassCleanup` (registered per resource, right after acquiring it),
   verified this session with a standalone repro that cleanups fire, and
   in the correct order, even when `setUpClass` raises.

Lesson: a design that passes its own proof and review can still be
incomplete — pushing back on scope, even after green checks, forced a
smaller and more correct design that a "ship it, it works" instinct would
have missed. First occurrence of this exact pattern in this project's
logs; watching for a second before promoting it to a standing rule.

## The next smallest slice
Per direct sign-off: start M4 — a first FastAPI endpoint wrapping the
existing `get_answer()` pipeline (Python 3.12 + FastAPI per ARCHITECT.md),
no SSE streaming or conversation/message persistence yet — the smallest
useful cut that proves the pipeline reachable over HTTP before adding
streaming and the `app` schema's SQLAlchemy read-write pool on top.
