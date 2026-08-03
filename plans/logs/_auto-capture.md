
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

## Commit at 2026-08-02 17:36
```
commit e63962a73c9a7f13017a95f34fc72ed2f2dd1ab1
Author: ng-aman <aman.roland@ngenux.com>
Date:   Sun Aug 2 17:36:45 2026 +0530

    Generate SQL from a fixed question: first link of M2's text-to-SQL pipeline
    
    For one hardcoded business question, app/pipeline/generate_sql.py builds
    the full olist catalog (all 9 tables' DDL + LLM description + columns) as
    schema context, calls Claude once via prompts/generate_sql.md, validates
    the {"sql": "..."} reply through a Pydantic model that only accepts a
    single SELECT statement (one retry, matching describe.py's pattern), and
    returns the raw SQL. verify_generate_sql.py is the done-check: confirms
    the SQL starts with SELECT and, via a hand-rolled alias-aware tokenizer
    (no sqlglot yet), that every table/column it references is real per a
    live catalog query.
    
    Reuses describe.py's fetch_tables/fetch_columns/format_columns_context/
    extract_json_object rather than duplicating them. Verified end-to-end:
    the generated SQL, executed directly against the real DB, returns 5
    correctly-ordered categories (see evals/generate_sql.md).
    
    Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/session_01RHYURdPacUjzbFPaPJdcwY

 app/pipeline/__init__.py                     |   0
 app/pipeline/generate_sql.py                 | 108 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 app/pipeline/verify_generate_sql.py          | 125 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 artifacts/reviews/2026-08-02-generate-sql.md | 138 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 evals/generate_sql.md                        |  59 +++++++++++++++++++++++++++++++++++++++++++++++++
 plans/briefs/2026-08-02-generate-sql.md      |  75 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 plans/logs/_auto-capture.md                  |  23 +++++++++++++++++++
 prompts/generate_sql.md                      |  29 ++++++++++++++++++++++++
 tests/_generate_sql_helpers.py               |  29 ++++++++++++++++++++++++
 tests/test_generate_sql_cli.py               | 148 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_generate_sql_prompt_file.py       |  93 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_verify_generate_sql_script.py     | 190 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 12 files changed, 1017 insertions(+)
```

## Commit at 2026-08-02 17:48
```
commit 32065a63554c62ab93663b2677cf0e68e2209273
Author: ng-aman <aman.roland@ngenux.com>
Date:   Sun Aug 2 17:48:18 2026 +0530

    Capture + handoff: generate-sql slice done, next brief is sqlglot validation
    
    Slice log for the generate-sql-from-a-fixed-question slice (commit
    e63962a), no-slop.md gains a checklist line requiring a matching eval for
    any new/changed prompt file (caught once this slice, promoted by explicit
    choice), and HANDOFF.md is rewritten with this session's verified state
    plus the next brief: a sqlglot-based validator replacing
    verify_generate_sql.py's regex tokenizer, per ARCHITECT.md's
    defense-in-depth ordering.
    
    Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/session_01RHYURdPacUjzbFPaPJdcwY

 HANDOFF.md                            | 296 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--------------------------------------------------------------------------------
 plans/logs/2026-08-02-generate-sql.md |  87 ++++++++++++++++++++++++++++++++++++++++++++++++
 plans/logs/_auto-capture.md           |  41 +++++++++++++++++++++++
 templates/no-slop.md                  |   4 +++
 4 files changed, 282 insertions(+), 146 deletions(-)
```

## Commit at 2026-08-02 19:29
```
commit cf0b452793b47acaeec459a72db235ff21a1ab91
Author: ng-aman <aman.roland@ngenux.com>
Date:   Sun Aug 2 19:29:21 2026 +0530

    sqlglot SQL validator: replace the regex reference-checker with real parsing
    
    Adds app/pipeline/validate_sql.py (validate_sql(sql, cur)): parses with
    sqlglot's Postgres dialect, rejects anything but a single SELECT, and
    checks every table/column reference against the live catalog -- table
    existence via an AST walk, column resolution via sqlglot's own
    scope-aware qualify(), which also correctly handles cases the old regex
    tokenizer couldn't (per-table ambiguity, ORDER BY output-alias
    references). verify_generate_sql.py now calls it instead of the deleted
    check_references/fetch_valid_names/regex constants.
    
    Four review passes on check_table_references each found one more way a
    cross-schema or cross-catalog reference could slip past a basename-only
    check (pg_catalog.products, a CTE name masking a qualified reference, a
    catalog..table double-dot form, and a case-folding mismatch) -- fixed by
    converging on an allowlist that combines every qualifier field sqlglot
    exposes and requires it equal exactly "olist" when present. Each fix has
    a regression test in ValidateSqlTests.
    
    Also extends test_llm_description_setup.py's dependency allowlist to
    include sqlglot (a second, separately pre-approved dependency per
    ARCHITECT.md), per explicit user decision on how to handle the resulting
    stale-test conflict.
    
    Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/session_01RHYURdPacUjzbFPaPJdcwY

 app/pipeline/validate_sql.py                 | 108 ++++++++++++++++++++++++++++++++++++++++++++++++++++
 app/pipeline/verify_generate_sql.py          |  95 ++-------------------------------------------
 artifacts/reviews/2026-08-02-validate-sql.md | 126 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 plans/briefs/2026-08-02-validate-sql.md      |  78 +++++++++++++++++++++++++++++++++++++
 requirements.txt                             |   1 +
 tests/test_llm_description_setup.py          |   5 +++
 tests/test_verify_generate_sql_script.py     | 328 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-----------------------------------------------
 7 files changed, 551 insertions(+), 190 deletions(-)
```

## Commit at 2026-08-02 19:39
```
commit 43b7b5b9a0323aea8b9fadc6cb08831417c92596
Author: ng-aman <aman.roland@ngenux.com>
Date:   Sun Aug 2 19:39:10 2026 +0530

    Capture + handoff: sqlglot validator slice done, next brief is asyncpg execution
    
    Slice log for the sqlglot-SQL-validator slice (commit cf0b452), a new
    no-slop.md checklist line (identifier/security validation should be an
    allowlist, not a blocklist -- promoted after the same bug shape recurred
    four times in one function this slice), and HANDOFF.md rewritten with
    this session's verified state plus the next brief: execute the validated
    SQL for real via a new read-only asyncpg connection with LIMIT/timeout
    injection, completing M2 Pipeline v0's full chain.
    
    Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/session_01RHYURdPacUjzbFPaPJdcwY

 HANDOFF.md                            | 275 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++---------------------------------------------------------------------------------------
 plans/logs/2026-08-02-validate-sql.md |  94 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 plans/logs/_auto-capture.md           |  69 +++++++++++++++++++++++++++++++++++++++++
 templates/no-slop.md                  |   9 ++++++
 4 files changed, 301 insertions(+), 146 deletions(-)
```

## Commit at 2026-08-02 20:39
```
commit 8fa281fb853679136cd76a4f2d89a9a4c2b9c2a2
Author: ng-aman <aman.roland@ngenux.com>
Date:   Sun Aug 2 20:39:18 2026 +0530

    Execute validated SQL for real via a read-only asyncpg connection
    
    Completes M2 Pipeline v0's full chain (question -> SQL -> validate ->
    execute -> printed answer) for the fixed question. execute_sql.py caps
    LIMIT to 1000 by editing the sqlglot AST (never loosening a tighter
    existing LIMIT) and executes through a fresh asyncpg connection
    authenticated as OLIST_RO_USER with a query-scoped 10s statement_timeout;
    answer.py chains generate_sql -> validate_sql -> execute_sql; verify_answer.py
    is the done-check CLI. Gate 2 record: artifacts/reviews/2026-08-02-execute-sql.md.
    
    Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/session_01RHYURdPacUjzbFPaPJdcwY

 app/pipeline/answer.py                      |  45 +++++++++++++++++++++++++++++++++++++++++++++
 app/pipeline/execute_sql.py                 |  55 +++++++++++++++++++++++++++++++++++++++++++++++++++++++
 app/pipeline/verify_answer.py               |  31 +++++++++++++++++++++++++++++++
 artifacts/reviews/2026-08-02-execute-sql.md | 135 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 plans/briefs/2026-08-02-execute-sql.md      |  77 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 requirements.txt                            |   1 +
 tests/_answer_helpers.py                    |  29 +++++++++++++++++++++++++++++
 tests/test_execute_sql_limit_cap.py         | 155 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_execute_sql_ro_role.py           | 109 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_execute_sql_statement_timeout.py |  42 ++++++++++++++++++++++++++++++++++++++++++
 tests/test_llm_description_setup.py         |   5 +++++
 tests/test_verify_answer_script.py          |  94 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 12 files changed, 778 insertions(+)
```

## Commit at 2026-08-02 20:46
```
commit ce458f5abcebdd9cd6906dab5b3e853b677182c6
Author: ng-aman <aman.roland@ngenux.com>
Date:   Sun Aug 2 20:46:48 2026 +0530

    Capture + handoff: execute-sql slice done, next brief is pgvector schema retrieval
    
    Slice log for the read-only asyncpg execution slice (commit 8fa281f), an
    ARCHITECT.md amendment naming Voyage AI as the embeddings provider (M3's
    retrieval work needs one picked), and HANDOFF.md rewritten with this
    session's verified state plus the next brief: embed table descriptions
    into pgvector and swap generate_sql.py's schema context from
    whole-catalog to top-k retrieval, the first link of M3.
    
    Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/session_01RHYURdPacUjzbFPaPJdcwY

 ARCHITECT.md                         |   4 +++
 HANDOFF.md                           | 268 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++----------------------------------------------------------------------------------
 plans/logs/2026-08-02-execute-sql.md |  80 +++++++++++++++++++++++++++++++++++++++++++++++++
 plans/logs/_auto-capture.md          |  60 +++++++++++++++++++++++++++++++++++++
 4 files changed, 278 insertions(+), 134 deletions(-)
```

## Commit at 2026-08-02 22:40
```
commit 92c76d9c690b01ff75e7f52c018e42391d179447
Author: ng-aman <aman.roland@ngenux.com>
Date:   Sun Aug 2 22:40:14 2026 +0530

    pgvector schema retrieval: swap generate_sql's context from full catalog to top-k
    
    app/catalog/embed.py embeds each table's existing LLM description via
    Voyage AI (voyage-3.5, 1024-dim) and upserts into a new pgvector table
    app.catalog_embeddings, idempotent like sync.py/describe.py; verify_embed.py
    is the matching done-check CLI. generate_sql.py's build_schema_context()
    now takes a pre-fetched table list instead of the whole catalog, fed by a
    new retrieve_relevant_tables() that embeds the fixed question and runs a
    pgvector top-k cosine-distance query (k=5 of 9 tables). Vector values move
    through plain psycopg2 as cast text literals -- no new pgvector python
    dependency, only voyageai (pinned, ARCHITECT.md's Voyage AI amendment).
    
    embed_text() gained a bounded rate-limit retry/backoff after this
    session's real Voyage account tripped its 3 RPM free-tier limit during
    the full test suite run; covered by dedicated fake-client unit tests
    added after the no-slop pass flagged the gap. Gate 2 record:
    artifacts/reviews/2026-08-02-pgvector-schema-retrieval.md.
    
    Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/session_01RHYURdPacUjzbFPaPJdcwY

 .env.example                                              |   1 +
 app/catalog/embed.py                                      | 117 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 app/catalog/verify_embed.py                               |  51 +++++++++++++++++++++++++++++++
 app/pipeline/generate_sql.py                              |  28 ++++++++++++++---
 artifacts/reviews/2026-08-02-pgvector-schema-retrieval.md | 174 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 plans/briefs/2026-08-02-pgvector-schema-retrieval.md      |  74 +++++++++++++++++++++++++++++++++++++++++++++
 requirements.txt                                          |   1 +
 tests/_embed_helpers.py                                   |  63 +++++++++++++++++++++++++++++++++++++++
 tests/test_catalog_embed.py                               | 234 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_env_example.py                                 |   5 ++++
 tests/test_generate_sql_cli.py                            | 100 +++++++++++++++++++++++++++++++++++++++++++++++--------------
 tests/test_llm_description_setup.py                       |   5 ++++
 tests/test_verify_embed_script.py                         | 126 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 13 files changed, 953 insertions(+), 26 deletions(-)
```

## Commit at 2026-08-02 23:35
```
commit 8ec527184ada2be5d9d9bd585f4c613fa7066bca
Author: ng-aman <aman.roland@ngenux.com>
Date:   Sun Aug 2 23:35:08 2026 +0530

    Capture + handoff: pgvector-schema-retrieval slice done, next brief is eval harness v1
    
    Slice log for the pgvector retrieval slice (commit 92c76d9), evals/generate_sql.md
    extended with a second case proving retrieval didn't regress SQL quality
    for the fixed question, and HANDOFF.md rewritten with this session's
    verified state plus the next brief: a 5-question eval harness
    (evals/questions.yaml + python -m evals.run) running the real pipeline,
    which requires generate_sql()/get_answer() to gain an optional question
    parameter (default FIXED_QUESTION, zero behavior change to existing
    CLI/verify scripts).
    
    Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/session_01RHYURdPacUjzbFPaPJdcwY

 HANDOFF.md                                         | 298 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--------------------------------------------------------------------
 evals/generate_sql.md                              |  37 ++++++++++++++-----
 plans/logs/2026-08-02-pgvector-schema-retrieval.md |  75 ++++++++++++++++++++++++++++++++++++++
 plans/logs/_auto-capture.md                        |  68 +++++++++++++++++++++++++++++++++++
 4 files changed, 336 insertions(+), 142 deletions(-)
```

## Commit at 2026-08-03 13:39
```
commit cd1edf049b4fa6329efc3430879aa2480f78fefe
Author: ng-aman <aman.roland@ngenux.com>
Date:   Mon Aug 3 13:39:30 2026 +0530

    Eval harness v1: run 5 curated questions through the real pipeline
    
    evals/run.py + evals/questions.yaml give the project its first automated
    accuracy number, per PRD.md's Section 10 eval spec. generate_sql()/
    get_answer() gain an optional `question` parameter (default
    FIXED_QUESTION) to unlock running more than the one fixed question, with
    zero behavior change to any existing CLI/verify script.
    
    Also bumps stop_verify.py's test-suite timeout from 300s to 1200s: the
    real suite now takes ~650-900s (real Voyage/Anthropic calls under rate
    limiting), so the old timeout was killing it mid-run on every agent turn,
    which can corrupt shared DB state used by pre-existing integration tests.
    
    Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/session_01RHYURdPacUjzbFPaPJdcwY

 .claude/hooks/stop_verify.py                    |  12 +++++++-
 app/pipeline/answer.py                          |  14 +++++-----
 app/pipeline/generate_sql.py                    |   6 ++--
 artifacts/reviews/2026-08-03-eval-harness-v1.md | 143 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 evals/__init__.py                               |   0
 evals/questions.yaml                            |  34 +++++++++++++++++++++++
 evals/run.py                                    |  99 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 plans/briefs/2026-08-02-eval-harness-v1.md      |  72 +++++++++++++++++++++++++++++++++++++++++++++++
 plans/logs/_auto-capture.md                     |  27 ++++++++++++++++++
 requirements.txt                                |   1 +
 tests/_eval_helpers.py                          |  33 ++++++++++++++++++++++
 tests/test_eval_questions_yaml.py               | 114 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_eval_run_cli.py                      |  88 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_eval_run_grading.py                  | 162 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_llm_description_setup.py             |  20 +++++++++++++
 tests/test_question_parameter.py                | 234 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 16 files changed, 1048 insertions(+), 11 deletions(-)
```

## Commit at 2026-08-03 14:15
```
commit 3e92b00dfed192f822a3e31f57a9f2fd438bc370
Author: ng-aman <aman.roland@ngenux.com>
Date:   Mon Aug 3 14:15:05 2026 +0530

    CLAUDE.md: note the test suite's real ~15min runtime
    
    Second-repetition ratchet from the eval-harness-v1 slice log: Voyage's
    rate limits have now caused friction in two consecutive slices (retry
    backoff, then a stop_verify.py timeout bug this suite's real runtime
    exposed). Documenting the real runtime so it's never mistaken for hung.
    
    Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/session_01RHYURdPacUjzbFPaPJdcwY

 CLAUDE.md | 2 ++
 1 file changed, 2 insertions(+)
```

## Commit at 2026-08-03 14:26
```
commit 695b796117499736e7253b5809dbea7f9e44117d
Author: ng-aman <aman.roland@ngenux.com>
Date:   Mon Aug 3 14:26:42 2026 +0530

    Capture + handoff: eval-harness-v1 slice done, next brief is glossary retrieval
    
    Slice log for the eval harness v1 slice (commit cd1edf0), and HANDOFF.md
    rewritten with this session's verified state plus the next brief:
    business glossary retrieval (F5), applying the same pgvector top-k
    pattern already built for schema retrieval to a seeded glossary.md of
    KPI definitions.
    
    Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/session_01RHYURdPacUjzbFPaPJdcwY

 HANDOFF.md                               | 321 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++----------------------------------------------------------------------------------
 plans/logs/2026-08-03-eval-harness-v1.md |  94 +++++++++++++++++++++++++++++++++++++++++++++++
 plans/logs/_auto-capture.md              |  61 +++++++++++++++++++++++++++++++
 3 files changed, 312 insertions(+), 164 deletions(-)
```

## Commit at 2026-08-03 19:12
```
commit a0005130451822ce941a56cad71e9b82de86099e
Author: ng-aman <aman.roland@ngenux.com>
Date:   Mon Aug 3 19:12:37 2026 +0530

    Business glossary retrieval: pgvector KPI context alongside schema context
    
    generate_sql() now retrieves top-k business-glossary entries (16 KPI
    definitions in glossary.md, embedded into app.kb_chunks via a new
    app/glossary/ package mirroring app/catalog/embed.py's convention) and
    threads them into the prompt alongside the existing schema retrieval, per
    PRD F5. Caught and fixed a real regression mid-slice: the first draft of
    two KPI definitions was too prescriptive and dropped the eval from 5/5 to
    3/5 by leaking into unrelated questions.
    
    Also bumps RATE_LIMIT_MAX_ATTEMPTS and several test/hook timeouts to
    absorb the doubled Voyage call load this adds to generate_sql().
    
    Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/session_01TH1p8fxBmrWtNJB18djsDk

 .claude/hooks/stop_verify.py                       |  25 +++++++++--------
 CLAUDE.md                                          |   4 ++-
 app/catalog/embed.py                               |  11 +++++++-
 app/glossary/__init__.py                           |   0
 app/glossary/embed.py                              | 103 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 app/glossary/verify_embed.py                       |  61 ++++++++++++++++++++++++++++++++++++++++
 app/pipeline/generate_sql.py                       |  40 ++++++++++++++++++++++++---
 artifacts/reviews/2026-08-03-glossary-retrieval.md | 159 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 glossary.md                                        | 152 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 plans/briefs/2026-08-03-glossary-retrieval.md      |  82 ++++++++++++++++++++++++++++++++++++++++++++++++++++++
 plans/logs/_auto-capture.md                        |  23 ++++++++++++++++
 prompts/generate_sql.md                            |   3 ++
 tests/_answer_helpers.py                           |  10 ++++++-
 tests/_generate_sql_helpers.py                     |  10 ++++++-
 tests/_glossary_helpers.py                         |  72 ++++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_describe_cli.py                         |  48 +++++++++++++++++++++++++-------
 tests/test_generate_sql_prompt_file.py             |  63 ++++++++++++++++++++++++++++++++++++++++++
 tests/test_glossary_embed.py                       | 228 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_glossary_parsing.py                     | 204 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_glossary_retrieval.py                   | 160 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_glossary_verify_embed.py                | 108 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 21 files changed, 1537 insertions(+), 29 deletions(-)
```

## Commit at 2026-08-03 19:22
```
commit dd3c5616f8f38ba35c345bf12b8176becef2230e
Author: ng-aman <aman.roland@ngenux.com>
Date:   Mon Aug 3 19:22:54 2026 +0530

    Add a glossary-driven eval case; unpin two tests' hardcoded 5-question count
    
    evals/questions.yaml gains a 6th question (average order value),
    specifically exercising a KPI whose correct SQL depends on glossary
    context -- per capture: this slice's own regression (glossary wording
    leaking into unrelated questions) was only caught by accident, since none
    of the original 5 questions specifically exercises glossary-informed KPI
    computation. Ripple effect: two tests hardcoded "exactly 5"/"N/5"
    assumptions that were always meant to be a floor, not a permanent
    ceiling, per templates/eval.md's own "start with 5; every production/demo
    failure adds a case" -- updated to check "at least 5" and "N/M" instead.
    
    Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/session_01TH1p8fxBmrWtNJB18djsDk

 evals/questions.yaml              | 17 +++++++++++++++--
 plans/logs/_auto-capture.md       | 46 ++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_eval_questions_yaml.py | 22 +++++++++++++---------
 tests/test_eval_run_cli.py        | 39 +++++++++++++++++++++++----------------
 4 files changed, 97 insertions(+), 27 deletions(-)
```
