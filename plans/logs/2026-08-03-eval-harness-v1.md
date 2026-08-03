# Slice log — eval harness v1

Date: 2026-08-03
Brief: plans/briefs/2026-08-02-eval-harness-v1.md

## The plan you approved
`generate_sql()`/`get_answer()` gain an optional `question` parameter
(default `FIXED_QUESTION`, zero behavior change to existing CLIs). New
`evals/run.py` (`load_questions`/`check_expected`/`format_summary`) loads
`evals/questions.yaml` (5 questions, hand-verified live against the real
`olist` DB) and runs each through the real pipeline, grading exact-match/
code-assertion only. `PyYAML` pinned as a new, Gate-1-confirmed dependency.

## The diff you accepted
Commit `cd1edf0` — "Eval harness v1: run 5 curated questions through the
real pipeline". 16 files changed, 1048 insertions(+), 11 deletions(-).
Full stat in `plans/logs/_auto-capture.md`. Also includes a disclosed,
out-of-brief fix: `.claude/hooks/stop_verify.py`'s test-suite timeout
300s → 1200s (see "rejected or changed" below).

## The done-check output
```
$ python -m evals.run
[PASS] What are the top 5 product categories by number of orders?
[PASS] Which payment type is used the most, by number of payments?
[PASS] Which customer state has the most customers?
[PASS] How many orders have the status 'delivered'?
[PASS] What is the average review score across all reviews?
5/5 correct
```
```
$ python -m unittest discover tests
.............................................................................................................................................
----------------------------------------------------------------------
Ran 139 tests in 651.003s

OK
```
(Full gate detail, including the two additional fresh-run attempts and
the recurring flake discussed below, in
`artifacts/reviews/2026-08-03-eval-harness-v1.md`.)

## One thing you rejected or changed
The test-writer subagent (working from the brief alone, blind to my
approved plan) delivered `evals/questions.yaml` as a top-level YAML list
and a `load_questions`/`check_expected`/`format_summary` function
contract — not the `{questions: [...]}` wrapper and `grade()`-returning-
a-tuple shape my own Gate-1 plan had proposed. Once the tests existed,
they were the actual spec: I built `evals/run.py` to match the
test-writer's contract rather than forcing my original shape, and
reconciled my planned `evals/questions.yaml` content (the 5 hand-verified
questions) into that shape instead.

Separately, and more significant: while verifying this slice's own
done-check, I discovered a real, previously-undiagnosed bug in
`.claude/hooks/stop_verify.py` (the harness's Stop hook, which re-runs
`python -m unittest discover tests` automatically on every agent turn).
Its 300s timeout was far shorter than the suite's real runtime (~650-900s
now, driven by real Voyage/Anthropic calls under rate limiting), so it
was silently killing the suite mid-run on every turn. A hard kill can
skip a test's `finally` cleanup — and two *pre-existing, unrelated* tests
(`test_catalog_sync.py`, `test_verify_describe_script.py`) mutate-then-
restore a shared DB row (`customers`'s description) as part of their own
checks. I fixed the timeout (300s → 1200s) and manually repaired the
corrupted row (twice, via `describe.py` regeneration) when I found it.
This is a genuine improvement, but investigation this session also
showed the corruption can still recur when two full-suite invocations
genuinely overlap in time (confirmed: a second fresh full-suite attempt
during the gate hit the same symptom even after the fix) — a deeper,
systemic concurrency hazard between the Stop hook's automatic re-runs
and this project's shared-mutable-DB integration test fixtures, not
something a timeout fix alone resolves. Fully solving that is out of
this slice's scope; flagging it as a standing open issue below rather
than chasing it further, per explicit user sign-off mid-session.

**Ratchet note:** this is the second time in two consecutive slices that
Voyage's free-tier rate limit has meaningfully slowed real test/eval
runs (first: `embed_text()`'s retry-with-backoff, prior slice; second:
this slice's ~650-900s full-suite runtime and the timeout bug it exposed).
Per CLAUDE.md's second-repetition rule, this is worth a standing note:
**any future slice/session should assume `python -m unittest discover
tests` takes up to ~15 minutes for real**, and should budget accordingly
rather than treating a long-running test command as hung.

## The next smallest slice
Business glossary retrieval (F5): apply the same pgvector top-k pattern
already built for schema retrieval (`app/catalog/embed.py`,
`retrieve_relevant_tables()`) to a business-glossary table, so
`generate_sql()` draws from two retrieval sources (schema + glossary)
instead of one. Sequenced ahead of the one-shot repair loop (PLAN.md's
other remaining M3 item) since it's the more direct extension of
already-built retrieval infrastructure, and the eval harness built this
slice now gives a concrete accuracy baseline to check the repair loop
against once that slice starts.
