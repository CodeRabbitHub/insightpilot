
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

## Commit at 2026-08-02 14:40
```
commit dbc77f10c595817bfe706715ba5e228d722134ea
Author: ng-aman <aman.roland@ngenux.com>
Date:   Sun Aug 2 14:40:26 2026 +0530

    Fix stop_verify hook to use project .venv, not the harness's own venv
    
    sys.executable inside a hook resolves to whatever interpreter launched
    it, which on this machine is the Claude Code harness's isolated internal
    venv (no pip, no project deps) -- not this project's Python environment.
    Once slice 1 added real dependencies (psycopg2-binary, python-dotenv),
    the hook's test run started failing with ModuleNotFoundError even though
    the tests themselves pass correctly under the project's own .venv.
    
    Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

 .claude/hooks/stop_verify.py | 10 +++++++++-
 plans/logs/_auto-capture.md  | 15 +++++++++++++++
 2 files changed, 24 insertions(+), 1 deletion(-)
```

## Commit at 2026-08-02 15:38
```
commit b55ae952353cb1c0789fe10e456e1f4b9bfb2a67
Author: ng-aman <aman.roland@ngenux.com>
Date:   Sun Aug 2 15:38:56 2026 +0530

    Catalog sync CLI: introspect olist schema into app.catalog_tables/columns
    
    python -m app.catalog.sync introspects every table/column in the seeded
    olist schema (types, nullability via a reconstructed ddl_summary,
    primary/foreign keys, live row counts, up to 5 distinct sample values
    per column) and persists it into two new app-schema tables matching
    PRD.md Â§7, so the future text-to-SQL pipeline (M2+) has a real catalog
    to validate generated SQL against. Truncate + reinsert per run, connects
    only as the owner role, no LLM calls or embeddings this slice.
    
    Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

 app/__init__.py                                  |   0
 app/catalog/__init__.py                          |   0
 app/catalog/sync.py                              | 221 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 app/catalog/verify_sync.py                       | 178 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 artifacts/reviews/2026-08-02-catalog-sync-cli.md | 106 ++++++++++++++++++++++++++++++++++++++++++++++++
 plans/briefs/2026-08-02-catalog-sync-cli.md      |  68 +++++++++++++++++++++++++++++++
 tests/_catalog_helpers.py                        | 127 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_catalog_sync.py                       | 334 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_verify_sync_script.py                 |  59 +++++++++++++++++++++++++++
 9 files changed, 1093 insertions(+)
```

## Commit at 2026-08-02 15:41
```
commit e71e2a2058ec62c5c7b6afaf11e27587fb99527d
Author: ng-aman <aman.roland@ngenux.com>
Date:   Sun Aug 2 15:41:03 2026 +0530

    Capture slice log for Catalog sync CLI
    
    Promotes a 2nd-repetition pattern to templates/no-slop.md: prove
    restricted/failure paths by actually triggering them, not by checking a
    config/grant/state proxy for them.
    
    Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

 plans/logs/2026-08-02-catalog-sync-cli.md | 87 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 templates/no-slop.md                      |  9 +++++++++
 2 files changed, 96 insertions(+)
```

## Commit at 2026-08-02 15:48
```
commit 0536c7dc168c58272c17e3ddc4b40ddfae2eb760
Author: ng-aman <aman.roland@ngenux.com>
Date:   Sun Aug 2 15:48:53 2026 +0530

    Handoff: catalog sync CLI done, next brief is LLM table descriptions
    
    Flags an open design question for the next slice: sync.py's
    TRUNCATE+reinsert of catalog_tables will wipe any cached LLM description
    on re-run, so that slice must resolve it (likely UPSERT on table_name)
    before implementation, not discover it mid-build.
    
    Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

 HANDOFF.md | 238 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--------------------------------------------------------------------------------
 1 file changed, 138 insertions(+), 100 deletions(-)
```

## Commit at 2026-08-02 16:49
```
commit a657fd6f03eff45226509fd83257ccbbe0602479
Author: ng-aman <aman.roland@ngenux.com>
Date:   Sun Aug 2 16:49:10 2026 +0530

    LLM table descriptions: describe.py generates + caches per-table Claude descriptions
    
    Finishes PRD F4/M1: one Claude Sonnet call per catalog_tables row, validated
    via Pydantic with one retry, skipping already-described rows so a second
    run costs zero LLM calls. Required changing sync.py from TRUNCATE to an
    UPSERT on table_name so re-syncing the olist schema never wipes a cached
    description.
    
    Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/session_01RHYURdPacUjzbFPaPJdcwY

 .env.example                                           |   2 ++
 app/catalog/describe.py                                | 171 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 app/catalog/sync.py                                    |  35 +++++++++++++++++-----
 app/catalog/verify_describe.py                         |  48 +++++++++++++++++++++++++++++
 artifacts/reviews/2026-08-02-llm-table-descriptions.md | 137 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 plans/briefs/2026-08-02-llm-table-descriptions.md      |  67 +++++++++++++++++++++++++++++++++++++++++
 plans/logs/_auto-capture.md                            |  90 +++++++++++++++++++++++++++++++++++++++++++++++++++++++
 prompts/table_description.md                           |  24 +++++++++++++++
 requirements.txt                                       |   2 ++
 tests/_describe_helpers.py                             |  58 +++++++++++++++++++++++++++++++++++
 tests/test_catalog_sync.py                             |  58 +++++++++++++++++++++++++++--------
 tests/test_describe_cli.py                             | 241 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_env_example.py                              |  17 +++++++++++
 tests/test_llm_description_setup.py                    | 109 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_verify_describe_script.py                   | 113 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 15 files changed, 1153 insertions(+), 19 deletions(-)
```

## Commit at 2026-08-02 17:21
```
commit ddfc51a059c6c2e17cb24a8fe5741613137a9339
Author: ng-aman <aman.roland@ngenux.com>
Date:   Sun Aug 2 17:21:40 2026 +0530

    Capture + handoff: LLM table descriptions slice
    
    Finishes the record for commit a657fd6: the slice log, eval, and
    HANDOFF.md rewrite were produced last session but never committed. No
    code changes -- evidence only, committed separately from the generate-sql
    slice to keep one-slice-per-commit intact.
    
    Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/session_01RHYURdPacUjzbFPaPJdcwY

 HANDOFF.md                                      | 290 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-------------------------------------------------------------------------
 evals/table_description.md                      |  48 ++++++++++++++++++++++++++
 plans/logs/2026-08-02-llm-table-descriptions.md |  84 +++++++++++++++++++++++++++++++++++++++++++++
 plans/logs/_auto-capture.md                     |  35 +++++++++++++++++++
 4 files changed, 319 insertions(+), 138 deletions(-)
```
