---
name: gate
description: Run the review gate on the current slice. Use before committing or merging any slice.
---

Run Gate 2: the five-check review that decides whether the slice merges.
The checks live in templates/review.md — walk them IN ORDER; each is a
cheap filter for the next.

1. CHECK 1 — size. Show git diff --stat. If the diff is too big to read
   line by line, stop here: propose how to split it and gate the pieces
   separately. Do not proceed with an unreviewable diff.
2. CHECK 2 — goal match. Restate the brief's Goal, then summarize what the
   diff actually does. Flag any mismatch in either direction (extra
   "improvements" are a mismatch too).
3. CHECK 3 — tests/evals. Run the brief's done-check FRESH (and the eval
   set if LLM behavior changed). Paste real output, never a summary.
4. CHECK 4 — no-slop. Dispatch the no-slop-reviewer subagent on the diff.
   Fix mechanical findings; present judgment findings to the user. No
   unresolved findings may remain.
5. CHECK 5 — shipping proof. Demonstrate it works in reality, not just in
   tests: run the actual command / hit the endpoint / render the page and
   attach the evidence.
6. Show the user the full diff and the five check results. Record their
   answers in templates/review.md fields — "Rejected or changed" must name
   at least one thing or justify zero.
7. Save to artifacts/reviews/YYYY-MM-DD-<slug>.md. Only a written "accept"
   verdict with all five checks green allows commit/merge. Reject or
   accept-with-changes → do the changes → re-gate the new diff.
