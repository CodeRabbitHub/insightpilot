---
name: capture
description: Write the slice log after the gate passes. Use right after committing a slice, before the handoff.
---

Record the evidence for the slice that just merged.

1. Read templates/log.md. Pre-fill the mechanical fields yourself:
   - Commit hash + stat: git log -1 --stat
   - Proof output: from the gate record in artifacts/reviews/, or
     plans/logs/_auto-capture.md (the post-commit hook appends there).
2. Ask the user only the judgment fields:
   - One thing rejected or changed (pre-fill from the gate record if there)
   - The next smallest slice (one sentence)
3. If this slice touched LLM behavior (prompt, model, retrieval), add or
   extend an eval using templates/eval.md — every quality issue found
   becomes a case. Note the eval file in the log.
4. If "rejected or changed" repeats a pattern from a previous log, propose
   the promotion: a new line in CLAUDE.md standing rules or
   templates/no-slop.md. Apply it if the user agrees.
5. Save to plans/logs/YYYY-MM-DD-<slug>.md.
