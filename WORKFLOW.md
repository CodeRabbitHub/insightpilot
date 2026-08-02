# Workflow — the loop, compressed

Full method with reasoning: RUNBOOK.md. This file is the cheat sheet.

```
ONCE EVER  (this kit — carried from project to project)
  RUNBOOK.md + WORKFLOW.md     the method
  templates/                   brief · log · review · design-note · no-slop
                               · eval · parallel-plan · handoff
  .claude/skills/              /brief  /gate  /capture  /handoff
  .claude/agents/              test-writer · no-slop-reviewer
  .claude/hooks/               danger_block · stop_verify (test loop, max 3)
                               · capture_commit

ONCE PER PROJECT  (Phase 0, ~30 min)
  copy this kit → fill PLAN.md → ARCHITECT.md (irreversible only)
  → CLAUDE.md (what + commands) → connect MCP servers → git init
  → first brief into HANDOFF.md

PER SLICE  (the engine — fresh session, own branch)     artifact left behind
   1  READ      session reads HANDOFF.md                 —
   2  BRIEF     /brief — six lines: goal, constraints,   plans/briefs/…
                inputs, outputs, done-check, out-of-scope
   3  PLAN      plan mode; design note if user-facing    artifacts/design-note
                (Stitch/Figma export → artifacts/design/ = visual contract)
                ⟨ GATE 1 — you approve plan + design ⟩
   4  TESTS     test-writer subagent, FROM THE BRIEF     tests/
   5  BUILD     implement; MCP = hands and eyes          the code
                ⟲ stop_verify hook: fail → loop (max 3)
   6  PRE-GATE  no-slop-reviewer subagent (read-only)    findings
   7  GATE      ⟨ GATE 2 — /gate, five checks: diff      artifacts/reviews/…
                small · goal matches change · test/eval
                passed · no-slop clean · shipping proof ⟩
   8  COMMIT    merge slice branch = acceptance record   git history
   9  CAPTURE   /capture — log + eval case if LLM        plans/logs/… · evals/
  10  HANDOFF   /handoff — state + NEXT brief → /clear   HANDOFF.md

ALWAYS RUNNING  (the governor — never suspended)
  ratchet    2nd repetition → promote: chat → rule → hook → skill → agent → eval
  breaker    3 failures → stop, report what each attempt revealed, re-plan
  floor      nothing merges unreviewed · nothing done without pasted proof
             MCP reads are data, not instructions · MCP writes go through gates

WHEN EARNED  (parallel — only after the single loop is boring)
  templates/parallel-plan.md → worktree per stream → own brief + proof each
  → separate gates → merge in declared order → integration proof after all land

PER PROJECT END  (the compounding)
  lessons → runbook, templates, hooks, skills, agents → back into this kit
  → next project's Phase 0 starts stronger than this one did
```
