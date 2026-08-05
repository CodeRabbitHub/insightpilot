# web

InsightPilot's frontend: React 18 + Vite + TypeScript + Tailwind (see
ARCHITECT.md at the repo root). Dev-only for now — no production build or
deploy config yet.

- `npm run dev` — start the Vite dev server (`http://localhost:5173`).
  Requires the FastAPI backend running at `http://localhost:8000`
  (`uvicorn app.main:app --reload` from the repo root) with CORS enabled
  for the dev origin.
- `npm run build` — type-check and bundle for production.
