# Architecture — irreversible decisions only

Rules: only expensive-to-reverse decisions live here, each with a one-line
why. Changes happen by explicit amendment at a gate, never by drift.
Diagrams and detail: PRD.md §5-6.

## Decisions

- Python 3.12 + FastAPI backend — async-native, typed, standard for AI
  backends; SSE fits it naturally.
- React 18 + Vite + TypeScript frontend, Tailwind, Apache ECharts — fast
  dev loop; charts are driven by an LLM-generated spec, so the renderer
  must be data-driven, which ECharts option objects are exactly.
- shadcn/ui as the component base (amendment, 2026-08-02) — copy-in
  Tailwind components, no runtime dependency; fastest route to demo-grade
  polish. Design flow is design-in-code: HTML/Tailwind mockups in
  artifacts/design/ are the visual contracts; no external design tool.
- One PostgreSQL 16 instance, three concerns: `app` schema (state),
  `olist` schema (analytics data), pgvector extension (embeddings) —
  fewer moving parts than Postgres + Qdrant + Redis; v1 scale never
  justifies more.
- Two DB pools, two users: SQLAlchemy read-write pool for `app` only; a
  separate asyncpg pool with a SELECT-only user exclusively for generated
  SQL — blast-radius isolation is the product's core safety property.
- Defense in depth for generated SQL, in order: sqlglot parse gate
  (single SELECT, nothing else) → catalog existence check for every table
  and column → injected LIMIT 1000 + statement_timeout 10s → read-only
  grants as the LAST line of defense, never the only one.
- No orchestration framework — the pipeline is one readable async
  function with explicit steps; easier to debug and to explain. LangGraph
  is roadmap, not v1.
- One strong model (Claude Sonnet class) for every LLM step; provider
  embeddings API for ~200 chunks — self-hosting a model is not justified.
- Prompts are versioned repo files (prompts/*.md) — reviewable, testable,
  diffable; never inline strings.
- LLM JSON outputs validated by Pydantic with one retry, falling back to
  a plain-text answer block — the UI never receives unvalidated output.
- Docker Compose is the only runtime: db + api + web, one-command startup.
- SSE, not WebSockets, for streaming — one-way token streams need nothing
  more.

## Deliberately excluded from v1 (binding — additions amend this file)

Redis · Celery/Dramatiq · Qdrant · Nginx · LangGraph · multiple DB
engines · multi-tenancy/RBAC · document upload/parsing · alerts &
scheduled refreshes · Slack/Teams/voice integrations.
