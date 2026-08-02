
## Commit at 2026-08-01 19:25
```
commit 89748a64c6627eac60508b1e534da215c6a65b2e
Author: Aman Roland <aman.roland@ngenux.com>
Date:   Sat Aug 1 19:25:46 2026 +0530

    Initial commit: FDE starter kit
    
    Agent-loop engineering kit: six-line briefs, five-check review gate,
    ten-category no-slop rubric, wired into Claude Code via 4 skills,
    2 subagents, and 3 lifecycle hooks. Method in RUNBOOK.md.
    
    Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

 .claude/agents/no-slop-reviewer.md |  28 +++
 .claude/agents/test-writer.md      |  21 ++
 .claude/hooks/capture_commit.py    |  38 ++++
 .claude/hooks/danger_block.py      |  39 ++++
 .claude/hooks/stop_verify.py       |  70 +++++++
 .claude/settings.json              |  36 ++++
 .claude/skills/brief/SKILL.md      |  22 +++
 .claude/skills/capture/SKILL.md    |  21 ++
 .claude/skills/gate/SKILL.md       |  29 +++
 .claude/skills/handoff/SKILL.md    |  19 ++
 .gitignore                         |   7 +
 ARCHITECT.md                       |  18 ++
 CLAUDE.md                          |  30 +++
 HANDOFF.md                         |  23 +++
 PLAN.md                            |  17 ++
 README.md                          |  53 +++++
 RUNBOOK.md                         | 391 +++++++++++++++++++++++++++++++++++++
 WORKFLOW.md                        |  51 +++++
 artifacts/design/.gitkeep          |   0
 artifacts/reviews/.gitkeep         |   0
 evals/.gitkeep                     |   0
 plans/briefs/.gitkeep              |   0
 plans/logs/.gitkeep                |   0
 templates/brief.md                 |  23 +++
 templates/design-note.md           |  23 +++
 templates/eval.md                  |  27 +++
 templates/handoff.md               |  22 +++
 templates/log.md                   |  21 ++
 templates/no-slop.md               |  75 +++++++
 templates/parallel-plan.md         |  25 +++
 templates/review.md                |  36 ++++
 tests/.gitkeep                     |   0
 32 files changed, 1165 insertions(+)
```

## Commit at 2026-08-02 13:22
```
commit 95a20c24ac0b1065ab7a4c7051c809b2cf32a45a
Author: ng-aman <aman.roland@ngenux.com>
Date:   Sun Aug 2 13:22:38 2026 +0530

    Initial commit: InsightPilot v1 project scaffold
    
    PRD, PLAN, ARCHITECT decisions, HANDOFF, and approved design contracts
    (chat-v1, dashboard-v1) for Phase 0. Includes kit machinery (.claude/
    skills, agents, hooks) and blank templates. No application code yet.

 .claude/agents/no-slop-reviewer.md |  28 ++++++++++++
 .claude/agents/test-writer.md      |  21 +++++++++
 .claude/hooks/capture_commit.py    |  38 +++++++++++++++++
 .claude/hooks/danger_block.py      |  39 +++++++++++++++++
 .claude/hooks/stop_verify.py       |  70 ++++++++++++++++++++++++++++++
 .claude/settings.json              |  36 ++++++++++++++++
 .claude/skills/brief/SKILL.md      |  22 ++++++++++
 .claude/skills/capture/SKILL.md    |  21 +++++++++
 .claude/skills/gate/SKILL.md       |  29 +++++++++++++
 .claude/skills/handoff/SKILL.md    |  19 +++++++++
 .gitignore                         |   3 ++
 ARCHITECT.md                       |  46 ++++++++++++++++++++
 CLAUDE.md                          |  46 ++++++++++++++++++++
 HANDOFF.md                         |  51 ++++++++++++++++++++++
 LICENSE                            |  21 +++++++++
 PLAN.md                            |  43 +++++++++++++++++++
 PRD.md                             | 204 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 README.md                          |  53 +++++++++++++++++++++++
 RUNBOOK.md                         | 391 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 WORKFLOW.md                        |  51 ++++++++++++++++++++++
 artifacts/design/.gitkeep          |   0
 artifacts/design/chat-v1.html      | 108 ++++++++++++++++++++++++++++++++++++++++++++++
 artifacts/design/dashboard-v1.html | 225 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 artifacts/design/design-note-v1.md |  46 ++++++++++++++++++++
 artifacts/reviews/.gitkeep         |   0
 evals/.gitkeep                     |   0
 plans/briefs/.gitkeep              |   0
 plans/logs/.gitkeep                |   0
 plans/logs/_auto-capture.md        |  49 +++++++++++++++++++++
 templates/brief.md                 |  23 ++++++++++
 templates/design-note.md           |  23 ++++++++++
 templates/eval.md                  |  27 ++++++++++++
 templates/handoff.md               |  22 ++++++++++
 templates/log.md                   |  21 +++++++++
 templates/no-slop.md               |  75 ++++++++++++++++++++++++++++++++
 templates/parallel-plan.md         |  25 +++++++++++
 templates/review.md                |  36 ++++++++++++++++
 tests/.gitkeep                     |   0
 38 files changed, 1912 insertions(+)
```

## Commit at 2026-08-02 14:21
```
commit 4e1745b96d7a28be2198042ef65dddf9bae0bd0c
Author: ng-aman <aman.roland@ngenux.com>
Date:   Sun Aug 2 14:21:35 2026 +0530

    Foundation DB + seed: Postgres 16 + pgvector, Olist data, RO user
    
    docker compose (single db service) brings up Postgres 16 with pgvector;
    scripts/seed.py idempotently loads the 9 Olist CSVs into typed tables
    under an `olist` schema and provisions a SELECT-only `olist_ro` role;
    scripts/verify_seed.py is the done-check (row counts vs CSVs, vector
    extension, olist_ro permission enforcement). Gate 2 accepted, see
    artifacts/reviews/2026-08-02-foundation-db-seed.md.
    
    Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

 .env.example                                       |   7 ++++++
 .gitignore                                         |   2 ++
 artifacts/reviews/2026-08-02-foundation-db-seed.md |  95 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 data/README.md                                     |  26 +++++++++++++++++++
 docker-compose.yml                                 |  16 ++++++++++++
 plans/briefs/2026-08-02-foundation-db-seed.md      |  47 +++++++++++++++++++++++++++++++++++
 plans/logs/_auto-capture.md                        |  53 +++++++++++++++++++++++++++++++++++++++
 requirements.txt                                   |   2 ++
 scripts/seed.py                                    | 204 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 scripts/verify_seed.py                             |  86 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 tests/_pg_helpers.py                               | 123 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_data_readme.py                          |  49 ++++++++++++++++++++++++++++++++++++
 tests/test_docker_compose.py                       |  76 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_env_example.py                          |  45 +++++++++++++++++++++++++++++++++
 tests/test_olist_ro_permissions.py                 | 144 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_require_env.py                          |  30 ++++++++++++++++++++++
 tests/test_seed_idempotency.py                     |  79 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_seed_schema.py                          |  70 ++++++++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_verify_seed_script.py                   |  43 ++++++++++++++++++++++++++++++++
 19 files changed, 1197 insertions(+)
```

## Commit at 2026-08-02 14:37
```
commit 76eda923274618a1365878bb605386c4f3f75d79
Author: ng-aman <aman.roland@ngenux.com>
Date:   Sun Aug 2 14:37:42 2026 +0530

    Handoff: foundation slice done, next brief is catalog sync CLI
    
    Records verified state of the Foundation DB + seed slice and writes the
    full brief for the next slice (app.catalog.sync introspection, LLM
    descriptions deferred to a later slice).
    
    Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

 HANDOFF.md | 159 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++------------------------------------------
 1 file changed, 117 insertions(+), 42 deletions(-)
```

## Commit at 2026-08-02 14:37
```
commit f5aa9b5c36abc6ff08b2533827edef3f965ea350
Author: ng-aman <aman.roland@ngenux.com>
Date:   Sun Aug 2 14:37:54 2026 +0530

    Capture slice log for Foundation DB + seed
    
    Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

 plans/logs/2026-08-02-foundation-db-seed.md | 65 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 plans/logs/_auto-capture.md                 | 57 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 2 files changed, 122 insertions(+)
```
