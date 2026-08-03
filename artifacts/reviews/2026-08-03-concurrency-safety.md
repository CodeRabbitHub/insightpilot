# Review gate — concurrency-safety

Date: 2026-08-04
Brief: plans/briefs/2026-08-03-concurrency-safety.md
Diff reviewed: uncommitted working tree (pre-commit) —
  tests/_pg_helpers.py, tests/test_verify_describe_script.py,
  tests/test_glossary_verify_embed.py, tests/verify_concurrency_safety.py
  (new), plans/briefs/2026-08-03-concurrency-safety.md (new)

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review
5 files (3 modified, 2 new), all mechanical and single-purpose. Read in
full over the course of the session. PASS.

## 2. The stated goal matches the actual change
Brief's Goal: make the two named racy tests
(`test_verify_describe_fails_when_a_description_is_missing`,
`test_verify_embed_fails_when_a_kb_chunk_is_missing`) safe under
concurrent full-suite invocation.

Actual change: each racy test file's `setUpClass` acquires a
session-scoped Postgres advisory lock (`pg_advisory_lock(hashtext(key))`)
immediately after opening its connection and before any shared-row
read/write (including its own `run_sync()`/`run_describe()` /
`run_glossary_embed()` calls), and releases it via `cls.addClassCleanup(...)`
rather than `tearDownClass` (which unittest skips entirely if `setUpClass`
raises). No individual test-method body changed. This fully serializes two
concurrent invocations of the same test class, which is what the brief's
goal requires in practice — the brief's literal constraint ("only add
locking around the two tests' mutation windows") turned out to be
insufficient on its own; see Rejected or changed. PASS.

## 3. The eval or test passed
Fresh, this session, final diff:
```
$ python -m tests.verify_concurrency_safety
  [OK] test_verify_describe_script.py (run 0): exit=0
  [OK] test_verify_describe_script.py (run 1): exit=0
  [OK] test_glossary_verify_embed.py (run 0): exit=0
  [OK] test_glossary_verify_embed.py (run 1): exit=0

verify_concurrency_safety: PASSED
```
```
$ python -m unittest discover tests
Ran 190 tests in 221.133s

OK
```
(Both re-run 3+ times across the session's design iterations, always
consistent. Full suite run in foreground/blocking, never
`run_in_background`, per HANDOFF.md's own mitigation note about racing the
Stop hook.)

## 4. The no-slop review found no unresolved issues
Five no-slop-reviewer passes, each on the diff as it stood at that point:
1. Found an incorrect docstring claim (`-m tests.verify_concurrency_safety`
   asserted not to work) — empirically wrong, verified and corrected; and
   a `proc.communicate(timeout=...)` that didn't kill the child on
   timeout, inconsistent with the codebase's `subprocess.run(timeout=...)`
   convention — fixed with explicit `proc.kill()` handling.
2. Confirmed both fixes landed; re-flagged the scope deviation (locking 3
   methods per file instead of 2) as present but deliberately left for the
   human gate.
3. Human rejected the 3-methods-per-file design at the gate. Redesigned to
   a class-level lock in `setUpClass`/`tearDownClass` (zero test-method
   bodies touched). Reviewer then found a genuine new bug: `setUpClass`
   called `run_describe()`/`run_glossary_embed()` *before* acquiring the
   lock, so a concurrent process's own (unlocked) setup could silently
   undo another process's in-progress mutation.
4. Confirmed the ordering fix; found a second genuine bug: `tearDownClass`
   never runs if `setUpClass` raises, leaking the session-scoped lock (and
   the connection) for the rest of that process's lifetime — exactly the
   stall this slice exists to prevent.
5. Confirmed the `addClassCleanup` fix (empirically verified this session
   with a standalone repro that cleanups fire even when `setUpClass`
   raises, and in the correct LIFO order — lock released before connection
   closes). Found one stale comment (an `acquire_advisory_lock` docstring
   still said "release in tearDownClass") — fixed.

No unresolved findings remain. PASS.

## 5. The shipping proof is attached
No separate UI/endpoint for test infrastructure — the done-check commands
in section 3 are the reality check: real Postgres, real concurrent OS
processes, no mocking anywhere in the fix or its proof.

## Rejected or changed
The human reviewer rejected the first accepted design (locking all 3
test methods per file, 6 total, via a per-method context manager) even
though it passed its own concurrency proof and no-slop review, on the
grounds that it touched more than the brief's named 2 tests. That
rejection forced a smaller, cleaner class-level design — which is what
surfaced two further, genuine bugs (the setUpClass ordering race and the
setUpClass-failure lock leak) that the rejected design's broader
after-the-fact locking had incidentally papered over. The final design is
smaller, more correct, and touches zero test-method bodies.

## Verdict
Accept.
