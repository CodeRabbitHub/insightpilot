# InsightPilot v1 — Product Requirements Document
**Version:** 1.0 · **Status:** Draft · **Owner:** You · **Target timeline:** 6–8 weeks (part-time)
---
## 1. Summary
InsightPilot v1 is a single-tenant, AI-powered analytics assistant. A user asks a business question in plain English; the system retrieves the database schema and business definitions, generates SQL, executes it safely against a read-only PostgreSQL database (Olist e-commerce dataset), renders a chart, and explains the result. Useful answers can be pinned to a dashboard.
**v1 explicitly is not** a multi-tenant SaaS. It is a polished, end-to-end vertical slice that demonstrates production-grade AI engineering: retrieval, text-to-SQL, validation, visualization, and persistence.
---
## 2. Goals & Non-Goals
### Goals
1. Answer natural-language questions about the Olist dataset with correct SQL ≥ 80% of the time on a curated test set of 30 questions.
2. Never execute a destructive or runaway query (100% enforcement via read-only role + validation + timeouts).
3. Full loop — question → SQL → result → chart → explanation — in under 15 seconds for typical queries.
4. Pinned dashboard cards persist and re-render on reload.
5. Demoable in under 3 minutes to a non-technical viewer.
### Non-Goals (deferred to roadmap)
- Multi-workspace / multi-tenant support
- Multiple database engines (PostgreSQL only)
- User invitations, roles, RBAC
- Document upload UI / PDF parsing (glossary is seeded, not uploaded)
- Alerts, scheduled refreshes, email reports
- Slack/Teams integrations, voice input
---
## 3. Users & Primary Use Cases
| User | v1 story |
|---|---|
| Analyst (primary) | "Ask a question, see the chart and SQL, trust the answer, pin it." |
| Executive (secondary) | "Open the dashboard, see current numbers." |
| Recruiter/reviewer (meta-user) | "Understand the architecture in 5 minutes from the README + demo." |
### Core user stories
1. As an analyst, I can type "Why did revenue drop in March 2018?" and get a numeric answer, a chart, and a plain-English explanation.
2. As an analyst, I can expand the generated SQL and read a line-by-line explanation of it.
3. As an analyst, I can click a suggested follow-up question to continue the investigation.
4. As an analyst, I can pin any answer to the dashboard as a card.
5. As any user, I can open the dashboard and see all pinned cards with fresh data.
6. As an analyst, I can revisit past conversations from a sidebar.
---
## 4. Functional Requirements
### F1 — Chat interface
- Single chat page with a message input, streaming assistant responses, and a conversation sidebar.
- Each assistant answer renders up to four blocks, in order: **summary sentence**, **chart** (if the result is chartable), **data table** (first 50 rows, collapsible), **explanation paragraph**.
- A collapsed "View SQL" section per answer shows the executed query with syntax highlighting and an AI-generated explanation.
- 3–5 suggested follow-up questions rendered as clickable chips under each answer.
- Empty state shows 6 starter questions (revenue trend, top categories, delivery times, top states, repeat rate, review scores).
### F2 — Text-to-SQL pipeline
Sequential pipeline (a plain async Python function, no framework):
1. **Classify** — is this answerable from the database? If not (small talk, out-of-scope), respond conversationally without SQL.
2. **Retrieve context** — top-k relevant table schemas (vector search over table/column descriptions) + top-k glossary entries (vector search over seeded KPI definitions).
3. **Generate SQL** — LLM call with schema context, glossary context, dialect notes, and few-shot examples. Output constrained to a single `SELECT`.
4. **Validate** — see F3. On failure, one automatic repair loop (error fed back to the LLM), max 2 attempts total.
5. **Execute** — read-only connection, `statement_timeout = 10s`, results capped at 1,000 rows.
6. **Analyze & respond** — second LLM call with the result sample: writes the summary, explanation, chart spec (chart type + axis mapping as JSON), and follow-up suggestions.
### F3 — SQL safety & validation (hard requirements)
- Database user is `SELECT`-only; no DDL/DML grants. This is the last line of defense, not the only one.
- Parse generated SQL with `sqlglot`; reject anything that is not a single `SELECT` statement (no `INSERT/UPDATE/DELETE/DROP/COPY/;` chaining).
- Verify every referenced table and column exists in the metadata catalog before execution.
- Enforce `LIMIT 1000` (inject if absent), `statement_timeout`, and a max result payload size.
- All executed SQL is logged with timestamp, duration, row count, and the originating question.
### F4 — Schema catalog
- On startup (or via a CLI command `python -m app.catalog.sync`), introspect the Olist database: tables, columns, types, primary/foreign keys, row counts, 5 sample values per column.
- Store the catalog in application tables; generate a one-paragraph natural-language description per table (LLM, run once, cached).
- Embed table descriptions + column names into pgvector for retrieval.
### F5 — Business glossary (lightweight RAG)
- A seeded `glossary.md` in the repo defining ~15 KPIs (Revenue, AOV, Repeat purchase rate, Delivery time, Review score, Churn proxy, etc.) with exact formulas referencing real Olist columns.
- Chunked per definition, embedded into pgvector, retrieved alongside schema context in F2.
- Demonstrates the RAG architecture without building document-upload/parsing infrastructure.
### F6 — Dashboard
- One default dashboard ("Overview").
- "Pin to dashboard" on any answer stores: title, SQL, chart spec, question text.
- Dashboard page renders cards in a responsive grid (2–3 columns); each card re-executes its stored SQL on page load ("fresh on view" — no background scheduler in v1).
- Card actions: rename, delete, "open originating chat".
### F7 — Conversations & persistence
- Conversations, messages, generated SQL, and pins persist in PostgreSQL.
- Sidebar lists conversations with auto-generated titles (first LLM summary of the opening question).
### F8 — Auth (minimal)
- Single hardcoded demo user with session cookie login (email + password from env vars). Enough for a login screen in the demo; no registration, no roles.
---
## 5. Architecture
```
┌─────────────┐     HTTPS      ┌──────────────────────────────┐
│  React SPA   │ ─────────────▶ │  FastAPI                     │
│  (Vite)      │  REST + SSE    │                              │
└─────────────┘                │  /chat  /dashboards  /catalog │
                               └──────┬───────────┬───────────┘
                                      │           │
                              LLM API │           │ asyncpg (RO user)
                                      ▼           ▼
                            ┌──────────────┐  ┌──────────────────┐
                            │  Claude API  │  │ PostgreSQL        │
                            └──────────────┘  │  ├─ app schema    │
                                              │  ├─ olist schema  │
                                              │  └─ pgvector ext  │
                                              └──────────────────┘
```
Design decisions:
- **One PostgreSQL instance, three concerns:** application state (`app` schema), the analytics dataset (`olist` schema, read-only user), and embeddings (pgvector). Fewer moving parts than Postgres + Qdrant + Redis.
- **Two DB connections in the backend:** a normal read-write pool for app tables, and a separate read-only pool (different DB user) exclusively for generated SQL.
- **No orchestration framework:** the pipeline is a readable async function with explicit steps. Easier to debug, easier to explain in interviews. LangGraph is a roadmap item, not a v1 need.
- **SSE streaming** for chat responses so the summary/explanation streams token-by-token.
---
## 6. Tech Stack
### Backend
| Choice | Why |
|---|---|
| Python 3.12 + FastAPI | Async-native, typed, standard for AI backends |
| SQLAlchemy 2.0 + Alembic | ORM for app tables, migrations |
| asyncpg | Direct driver for executing generated SQL (bypasses ORM by design) |
| Pydantic v2 | Request/response models + validating LLM JSON outputs |
| sqlglot | SQL parsing/validation/AST inspection of generated queries |
| pgvector | Embeddings storage + similarity search inside Postgres |
### AI
| Choice | Why |
|---|---|
| Claude Sonnet (or GPT-4-class equivalent) via API | SQL generation, analysis, explanations; one strong model for everything in v1 |
| Provider embeddings API (e.g., voyage / text-embedding-3-small) | ~200 embedded chunks total — trivially cheap; avoids hosting a model |
| Prompt files in repo (`prompts/*.md`) | Versioned, reviewable, testable prompts |
### Frontend
| Choice | Why |
|---|---|
| React 18 + Vite + TypeScript | Fast dev loop, typed API client |
| TanStack Query | Server-state caching for conversations/dashboards |
| Apache ECharts | Bar/line/pie/table rendering driven by the LLM chart spec |
| Tailwind CSS | Speed; consistent polish |
| react-grid-layout | Dashboard card grid (static layout acceptable for v1) |
### Infrastructure
| Choice | Why |
|---|---|
| Docker Compose | `db` (postgres:16 + pgvector) + `api` + `web`; one-command startup |
| Seed scripts | `make seed` downloads Olist CSVs, loads `olist` schema, creates RO user, syncs catalog, embeds glossary |
| GitHub Actions | Lint (ruff), type-check (mypy), tests on push |
Deliberately excluded from v1: Redis, Celery/Dramatiq, Qdrant, Nginx, LangGraph, Snowflake/BigQuery connectors.
---
## 7. Data Model (app schema)
```
users            (id, email, password_hash, created_at)
conversations    (id, user_id, title, created_at)
messages         (id, conversation_id, role, content_json, created_at)
queries          (id, message_id, sql_text, status, duration_ms,
                  row_count, error_text, created_at)
dashboards       (id, name, created_at)
dashboard_cards  (id, dashboard_id, title, question_text, sql_text,
                  chart_spec_json, position, created_at)
catalog_tables   (id, table_name, description, row_count, ddl_summary)
catalog_columns  (id, table_id, column_name, data_type, is_pk, is_fk,
                  ref_table, sample_values_json)
kb_chunks        (id, source, content, embedding vector(1536))
```
`content_json` on messages stores the full structured answer (summary, chart spec, table sample, explanation, follow-ups) so history re-renders without re-execution.
---
## 8. API Surface
```
POST   /api/auth/login
POST   /api/auth/logout
GET    /api/conversations
POST   /api/conversations
GET    /api/conversations/{id}
POST   /api/conversations/{id}/messages     → SSE stream of answer blocks
GET    /api/dashboards/{id}                 → cards with fresh data
POST   /api/dashboards/{id}/cards           → pin
PATCH  /api/cards/{id}                      → rename/position
DELETE /api/cards/{id}
POST   /api/cards/{id}/run                  → re-execute one card
GET    /api/catalog/tables                  → for a schema browser page (stretch)
```
---
## 9. Key Prompts (repo artifacts)
1. `classify.md` — route: `sql_question | conversational | out_of_scope`.
2. `generate_sql.md` — schema context + glossary + dialect rules + 6 few-shot Olist examples → single SELECT.
3. `repair_sql.md` — failed SQL + DB error → corrected SELECT.
4. `analyze.md` — question + SQL + result sample → JSON: `{summary, explanation, chart_spec, follow_ups[]}` (validated by Pydantic; one retry on invalid JSON).
5. `explain_sql.md` — SQL → beginner-friendly explanation.
---
## 10. Quality, Evaluation & Observability
- **Eval set:** `evals/questions.yaml` — 30 curated questions with expected result assertions (e.g., "top category by 2018 revenue == beleza_saude"). Script runs the full pipeline and reports accuracy. This is the project's headline engineering artifact.
- **Targets:** ≥ 80% correct on eval set; ≥ 95% of generated queries pass validation on first or repair attempt; p50 end-to-end latency < 8s, p95 < 15s.
- **Logging:** every pipeline run logs step timings, token counts, SQL, and outcome to the `queries` table; a simple `/api/admin/stats` endpoint summarizes them.
---
## 11. Risks & Mitigations
| Risk | Mitigation |
|---|---|
| Wrong-but-confident SQL answers | Always show SQL + row sample; eval set; repair loop; "AI-generated — verify before decisions" label on answers |
| Olist schema quirks (order items grain, payment vs order totals) | Encode grain rules explicitly in the glossary and few-shot examples |
| LLM JSON output breaks UI | Pydantic validation with one retry; fallback to plain-text answer block |
| Latency feels slow | Stream summary first; run chart-spec generation in the same call; cache schema context per conversation |
| Cost creep during development | Cap context (top-k retrieval, 50-row result samples); log token usage per run |
---
## 12. Milestones
| Week | Deliverable |
|---|---|
| 1 | Docker Compose up; Olist loaded; RO user; catalog sync CLI; schema descriptions generated |
| 2 | Pipeline v0 end-to-end in CLI: question → SQL → validate → execute → printed answer |
| 3 | Retrieval (pgvector schema + glossary), repair loop, eval harness with first accuracy number |
| 4 | FastAPI endpoints + SSE streaming; persistence of conversations/messages |
| 5 | React chat UI: messages, charts (ECharts), SQL viewer, follow-up chips |
| 6 | Dashboard: pin, grid, fresh-on-view execution, card actions |
| 7 | Login, polish, empty states, error states, latency tuning |
| 8 | Eval pass to ≥80%, README with architecture diagram + GIF demo, deploy (single VPS or Fly.io) |
---
## 13. Definition of Done (v1)
- `docker compose up` + `make seed` produces a working app from a clean clone.
- All 6 starter questions produce correct, charted, explained answers.
- Eval score ≥ 80% documented in the README.
- Zero non-SELECT statements can reach the analytics database (covered by unit tests attempting injection/DDL).
- Dashboard with ≥ 4 pinned cards survives restart and re-renders with fresh data.
- README covers: problem, demo GIF, architecture, pipeline diagram, eval results, roadmap (the full original vision doc becomes the roadmap section).
