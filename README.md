# InsightPilot

InsightPilot is a single-tenant, AI-powered analytics assistant. You ask a
business question in plain English; it retrieves the relevant database
schema and business definitions, generates SQL, validates and executes it
against a read-only PostgreSQL database, then returns a chart and a plain-
English explanation. Useful answers can be pinned to a dashboard.

It's built over the [Olist Brazilian e-commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
as a concrete, realistic analytics domain — orders, customers, products,
payments, reviews, deliveries.

This is a **polished vertical slice, not a multi-tenant SaaS product**. The
goal is to demonstrate production-grade AI engineering end to end: retrieval,
text-to-SQL generation, validation, visualization, and persistence. Full
requirements and non-goals live in `PRD.md`.

## Key features

- **Ask questions in plain English** — "Which payment type is used the most?",
  "What is the average review score across all reviews?" — no SQL required.
- **Retrieval-grounded SQL generation** — the LLM writes SQL with real schema
  context (introspected table/column descriptions) and a seeded business
  glossary of ~15 KPI definitions (Revenue, AOV, delivery time, ...), both
  retrieved via pgvector similarity search, not passed in whole.
- **Defense-in-depth SQL safety** — every generated query passes a `sqlglot`
  parse gate (single `SELECT` only, no DDL/DML/statement-chaining), a catalog
  existence check for every table/column it references, an injected
  `LIMIT 1000` and `statement_timeout`, and finally runs through a database
  role that only has `SELECT` grants — four independent layers, not one.
- **Self-repair** — if generated SQL fails validation or execution, the error
  is fed back to the LLM for one automatic repair attempt before giving up.
- **Chart + explanation, not just a table** — each answer includes a summary
  sentence, an LLM-chosen chart spec, the underlying data, and a plain-English
  explanation of both the result and the SQL that produced it.
- **Conversations that persist** — questions, answers, and generated SQL are
  stored in Postgres and streamed to the browser over SSE as they're produced.
- **An accuracy eval, not just unit tests** — `evals/questions.yaml` is a
  curated set of real questions with hand-verified expected answers; the
  pipeline's actual accuracy against them is the project's headline metric
  (target: ≥ 80%, see `PRD.md` §10).

## How the pipeline works

```
question (plain English)
      │
      ▼
 classify            — is this answerable from the database at all?
      │
      ▼
 retrieve context     — pgvector search over schema descriptions + the
      │                  seeded business glossary (KPI definitions)
      ▼
 generate SQL         — LLM call constrained to a single SELECT
      │
      ▼
 validate             — sqlglot parse gate + catalog existence check +
      │                  injected LIMIT/timeout; one automatic repair
      │                  loop on failure
      ▼
 execute              — read-only asyncpg pool, isolated from the app's
      │                  read-write pool
      ▼
 analyze & respond     — chart spec + summary + explanation + follow-ups
      │
      ▼
 chart + explanation, streamed to the browser (SSE); optionally pinned
 to a dashboard card
```

The pipeline is a plain async Python function with explicit steps — no
agent framework. See `ARCHITECT.md` for why, and `PRD.md` §5-6 for the
full architecture and tech-stack rationale.

## Architecture

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

One Postgres 16 instance holds three concerns: application state (`app`
schema, read-write), the analytics dataset (`olist` schema, read-only
user), and embeddings (pgvector). Generated SQL only ever runs through the
read-only pool, only after passing sqlglot validation and a catalog
existence check — never through the app's ORM pool, never raw. That
isolation is the product's core safety property; see `ARCHITECT.md` for the
full list of binding decisions (and what's deliberately excluded, e.g.
Redis, Celery, Qdrant, LangGraph — not needed at this scale).

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 + Alembic, asyncpg, Pydantic v2 |
| SQL safety | sqlglot (parse/validate generated SQL) |
| AI | Claude (SQL generation, analysis, explanations), Voyage AI (embeddings) |
| Retrieval | pgvector inside the same Postgres instance |
| Frontend | React 18 + Vite + TypeScript, Tailwind CSS, Apache ECharts |
| Infra | Docker Compose (Postgres + pgvector); API and web run directly today |

## Setup

Requirements: Docker, Python 3.12, Node.js, and API keys for Anthropic
(Claude) and Voyage AI.

1. **Clone and configure**
   ```
   cp .env.example .env
   # fill in ANTHROPIC_API_KEY, VOYAGE_API_KEY, and DB credentials
   ```
2. **Start Postgres** (image includes the pgvector extension)
   ```
   docker compose up -d
   ```
3. **Install Python dependencies**
   ```
   pip install -r requirements.txt
   ```
4. **Load the Olist dataset** — downloads/loads the CSVs into the `olist`
   schema and creates the read-only DB role used for all generated SQL:
   ```
   python scripts/seed.py
   ```
5. **Build the schema catalog** — introspects `olist`, generates one LLM
   description per table, and embeds everything for retrieval:
   ```
   python -m app.catalog.sync
   python -m app.catalog.describe
   python -m app.catalog.embed
   ```
6. **Embed the business glossary** (`glossary.md` → pgvector):
   ```
   python -m app.glossary.embed
   ```
7. **Apply app-schema migrations** (conversations, messages, ...):
   ```
   alembic upgrade head
   ```

## Running it

Backend (dev server with reload):
```
uvicorn app.main:app --reload
```
Frontend (`web/`):
```
cd web && npm install && npm run dev
```
The Vite dev server runs on `http://localhost:5173` and talks to the API on
`http://localhost:8000` (CORS is scoped to exactly that origin).

## Usage

Ask a question directly against the API without the UI:
```
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the top 5 product categories by number of orders?"}'
```
This runs the full pipeline and returns a JSON answer (summary, chart spec,
result rows, explanation, follow-up questions). `POST /api/ask/stream` returns
the same answer as an SSE stream instead of a single JSON blob.

Conversation-scoped usage (what the web UI drives):
```
POST /api/conversations                         # create a conversation
POST /api/conversations/{id}/messages            # ask within it (SSE)
GET  /api/conversations                          # list past conversations
GET  /api/conversations/{id}                      # a conversation's full history
```
See `PRD.md` §8 for the complete API surface (dashboards/cards are specified
but not yet wired into the frontend — see Current status).

Six starter questions to try (also the eval set's core cases — see
`evals/questions.yaml`): revenue trend, top product categories, delivery
times, top customer states, repeat purchase rate, average review score.

## Current status

Backend pipeline (question → SQL → validation → execution → chart spec +
explanation), persistence (conversations/messages in the `app` schema), and
the streaming `/api/ask` and `/api/conversations/*` endpoints are built.
The frontend has a working React/Vite/Tailwind scaffold with a read-only
conversation list and detail view; message composing, SSE consumption in
the browser, chart rendering, and the dashboard page are still in progress.
See `HANDOFF.md` for exact state and the next slice, and `PLAN.md` for the
full milestone list (M1-M8).

## Project structure

```
app/
  main.py           FastAPI app: /api/ask, /api/ask/stream, /api/conversations/*
  pipeline/         generate_sql, validate_sql, execute_sql, repair_sql, answer
  catalog/          schema introspection, LLM table descriptions, embeddings
  glossary/         business glossary embedding
  db/               SQLAlchemy models + sessions (app schema)
web/                React + Vite + Tailwind frontend
prompts/            versioned LLM prompts (generate_sql.md, repair_sql.md, ...)
glossary.md         seeded KPI definitions (the RAG content for F5)
evals/               questions.yaml + the eval harness (python -m evals.run)
tests/              unit/integration tests (real DB + LLM calls)
scripts/            seed.py, verify_seed.py
alembic/            app-schema migrations
```

## Docs map

| Doc | Purpose |
|---|---|
| `PRD.md` | Requirements: goals, functional specs, API surface, data model |
| `ARCHITECT.md` | Irreversible decisions and what's deliberately excluded |
| `PLAN.md` | Milestones |
| `HANDOFF.md` | Current state + the next unit of work |
| `glossary.md` | Seeded business KPI definitions (the RAG content for F5) |
| `prompts/` | Versioned LLM prompts used by the pipeline |
| `evals/questions.yaml` | Curated eval questions with expected-answer assertions |

## Development method

This repo is built slice-by-slice using the FDE workflow: a written brief
per slice, tests before implementation, a review gate before every commit,
and a handoff that carries context to the next session. See `RUNBOOK.md`
for the full method and `WORKFLOW.md` for the compressed day-to-day loop.
