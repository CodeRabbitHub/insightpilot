# FDE Starter Kit

A copyable operating system for building projects with AI agents:
contracts before code, evidence over claims, two human gates per slice,
and automation that compounds. Method: RUNBOOK.md. Cheat sheet: WORKFLOW.md.

## Start a new project

1. Copy this whole folder and rename it to your project.
2. Fill in PLAN.md (goal + milestones) and ARCHITECT.md (irreversible
   decisions only).
3. Fill the "What this project is" and Commands sections of CLAUDE.md.
4. `git init` and commit the docs.
5. Open Claude Code and run `/brief` to write the first slice — or fill
   the brief inside HANDOFF.md by hand.
6. Follow the loop in WORKFLOW.md.

## What's wired up out of the box

| Piece | What it does |
|---|---|
| `/brief` | Interviews you into a slice contract; refuses vague done checks |
| `/gate` | Runs the reviewer subagent, shows diff + fresh proof, records your verdict |
| `/capture` | Writes the slice log; mechanics pre-filled, judgment asked |
| `/handoff` | Rewrites HANDOFF.md with verified state + the next brief |
| test-writer agent | Writes tests from the brief only, before implementation |
| no-slop-reviewer agent | Read-only diff review against templates/no-slop.md |
| danger_block hook | Blocks rm -rf, force push, hard reset, .env writes |
| stop_verify hook | Agent can't claim "done" while tests fail; 3 strikes → forced re-plan |
| capture_commit hook | Appends every commit's stat to plans/logs/_auto-capture.md |

## Adapting the kit

- **Different test runner?** Edit `TEST_CMD` in `.claude/hooks/stop_verify.py`
  and the Test command in CLAUDE.md. (Hooks require `python` on PATH.)
- **New slop pattern caught twice?** Add a line to `templates/no-slop.md` —
  the reviewer agent reads it as its rubric, so reviews improve instantly.
- **New standing rule?** One line in CLAUDE.md. Rule keeps getting violated?
  Promote it to a hook.
- Templates are the single source of truth: skills and agents reference
  them, never copy them. Edit the template, everything downstream follows.

## Layout

```
CLAUDE.md  PLAN.md  ARCHITECT.md  HANDOFF.md   the project's head
RUNBOOK.md  WORKFLOW.md                        the method
templates/                                     blank forms (source of truth)
plans/briefs/  plans/logs/                     contracts and evidence
artifacts/reviews/  artifacts/design/          gate records, visual contracts
evals/  tests/                                 quality checks
.claude/skills|agents|hooks + settings.json    the machinery
```
