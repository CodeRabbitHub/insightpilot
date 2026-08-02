# Handoff

Date: 2026-08-02
Slice just completed: none — Phase 0 just finished.

## State of the work
- PRD.md written (full v1 requirements, 8-week milestone map).
- PLAN.md: 8 milestones, M1 = foundation (compose, seed, RO user, catalog).
- ARCHITECT.md: 12 decisions recorded; "deliberately excluded" list is
  binding.
- CLAUDE.md: commands + project-specific standing rules (SQL safety,
  prompt/eval discipline).
- Kit machinery copied in (.claude/ skills, agents, hooks, templates/).
- Design contracts APPROVED (2026-08-02): artifacts/design/chat-v1.html
  and dashboard-v1.html are the binding visual contracts for M5/M6;
  decision + debts in artifacts/design/design-note-v1.md. shadcn/ui
  adopted by ARCHITECT.md amendment.
- No code exists. Repo not yet initialized (git init is the next manual
  step).

## Proof
n/a — nothing built yet.

## Open questions / known issues
- Olist CSVs come from Kaggle (auth needed for API download) — slice 1
  allows a manual data/ drop as fallback; decide during the slice.
- Test runner: kit hook runs unittest; project will likely move to pytest
  when FastAPI test deps land — that slice must update
  .claude/hooks/stop_verify.py TEST_CMD and CLAUDE.md together.
- Expected Olist row counts for verify_seed.py to assert (orders ≈
  99,441) — confirm exact numbers from the downloaded CSVs during slice 1.

## Next slice (the brief)
Goal: From a clean clone, `docker compose up` plus one seed command
  produce a Postgres 16 + pgvector instance with the full Olist dataset
  in an `olist` schema and a SELECT-only `olist_ro` user.
Constraints: postgres:16 + pgvector image; seed idempotent (safe to
  re-run); olist_ro gets zero DDL/DML grants; CSVs live in data/
  (manual Kaggle download acceptable — document it in data/README.md);
  seed scripts use plain psycopg/asyncpg, no ORM; secrets via .env,
  .env.example committed.
Inputs: PRD.md §5-6 and §12 week 1; the 9 Olist CSV files from Kaggle;
  Docker Desktop.
Outputs: docker-compose.yml (db service only for now), scripts/seed.py,
  scripts/verify_seed.py, .env.example, data/README.md.
Done-check: python scripts/verify_seed.py — exits 0 only if all 9 olist
  tables exist with expected row counts, the vector extension is
  installed, and an INSERT attempted as olist_ro raises a permissions
  error.
Out-of-scope: catalog sync and table descriptions, embeddings/glossary,
  any LLM call, the app schema and its tables, FastAPI, frontend, CI.
