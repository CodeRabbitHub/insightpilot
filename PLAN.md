# Plan — InsightPilot v1

Goal: a single-tenant AI analytics assistant. A user asks a business
question in plain English; the system retrieves schema + business
definitions, generates SQL, executes it safely against a read-only
PostgreSQL (Olist e-commerce dataset), renders a chart, and explains the
result. Useful answers pin to a dashboard.

Not a multi-tenant SaaS — a polished end-to-end vertical slice that
demonstrates production-grade AI engineering: retrieval, text-to-SQL,
validation, visualization, persistence. Full requirements: PRD.md.

For: an analyst who wants trustworthy charted answers; an executive who
opens the dashboard; a reviewer who must grasp the architecture in 5
minutes from the README + demo.

## Milestones

- M1 Foundation: docker compose up; Olist loaded into `olist` schema;
      SELECT-only user; catalog sync CLI; LLM table descriptions cached.
- M2 Pipeline v0 in the CLI: question → SQL → validate → execute →
      printed answer. No retrieval yet — schema context passed whole.
- M3 Retrieval + repair + evals: pgvector search over catalog + glossary,
      one-shot repair loop, eval harness with the first accuracy number.
- M4 API: FastAPI endpoints, SSE streaming, conversations/messages
      persisted in the app schema.
- M5 Chat UI: React chat page — messages, ECharts, SQL viewer with
      explanation, follow-up chips, starter questions.
- M6 Dashboard: pin answers, responsive card grid, fresh-on-view
      re-execution, card actions.
- M7 Auth + polish: demo login, empty/error states, latency tuning
      (p50 < 8s, p95 < 15s).
- M8 Ship: eval pass to ≥ 80%, README with architecture diagram + demo
      GIF, deploy to a single VPS or Fly.io.

## Proof (project-level — from PRD Definition of Done)

- `docker compose up` + seed command produce a working app from a clean clone.
- All 6 starter questions produce correct, charted, explained answers.
- Eval score ≥ 80% on evals/questions.yaml, documented in the README.
- Zero non-SELECT statements can reach the analytics DB (injection/DDL
  unit tests prove it).
- A dashboard with ≥ 4 pinned cards survives restart and re-renders fresh.
