# Brief — react-vite-scaffold

Date: 2026-08-05
Milestone: M5 Chat UI (scaffold slice — stands up the frontend toolchain
against the existing read-only API; the actual chat page with SSE and
ECharts follows in later M5 slices)

Goal:
Stand up the React 18 + Vite + TypeScript + Tailwind frontend (per
ARCHITECT.md's decision) in a new `web/` directory, with exactly one page
that lists real conversations via `GET /api/conversations` and, on
clicking one, shows its messages via `GET /api/conversations/{id}` —
proving the frontend toolchain and the read-only API surface built over
the last three slices end-to-end, in a real browser, for the first time.

Constraints:
- Stack exactly as ARCHITECT.md decided: React 18, Vite, TypeScript,
  Tailwind. These are pre-approved architecture decisions, not new
  dependencies needing to ask.
- No shadcn/ui components yet — ARCHITECT.md names it as the eventual
  component base, but this scaffold slice only needs a readable list and
  a detail pane; defer installing it to the slice that actually needs
  polished components.
- No routing library (react-router or similar) — a new dependency
  decision, deferred. Use local component state (the selected
  conversation id) to switch between list and detail views instead of
  URL-based routing.
- No message composing, no `POST` calls, no SSE consumption — this
  slice is read-only against the two `GET` endpoints only.
- No ECharts, no chart rendering — `content_json` is raw SQL text and a
  row array, not a chart spec yet; render it as plain text/a simple
  table, nothing fancier.
- FastAPI needs CORS enabled for the Vite dev server's origin
  (`http://localhost:5173`, Vite's default) to call it in local dev —
  add `CORSMiddleware` to `app/main.py`, scoped to exactly that one
  origin, dev-only. This is the one necessary backend touch; every
  existing route stays otherwise unchanged.
- No new backend dependencies. New frontend dependencies limited to
  exactly what ARCHITECT.md already named (`react`, `vite`,
  `typescript`, `tailwindcss`) plus their own standard build tooling
  (e.g. `@vitejs/plugin-react`, `autoprefixer`, `postcss`) — nothing
  else without asking first.
- No docker-compose wiring for the "web" service, no production build or
  deploy config — dev-server-only (`npm run dev`) for this slice.

Inputs:
- ARCHITECT.md's frontend stack decision (React 18 + Vite + TypeScript +
  Tailwind; shadcn/ui deferred per Constraints above).
- A running FastAPI dev server (`uvicorn app.main:app --reload`) and its
  `GET /api/conversations` / `GET /api/conversations/{id}` endpoints
  (previous slice, already merged) to call from the browser.
- PRD.md §5 (architecture diagram: React SPA via Vite, REST + SSE to
  FastAPI) and §8 (API surface).
- `app/main.py` — where `CORSMiddleware` is added.

Outputs:
- New `web/` directory: a working Vite + React + TypeScript + Tailwind
  scaffold (`package.json`, `vite.config.ts`, `tsconfig.json`,
  `tailwind.config.*`, `src/`).
- One page/component that, on load, calls `GET /api/conversations` and
  renders the list (id, title-or-"Untitled", created_at); clicking an
  item calls `GET /api/conversations/{id}` and renders its messages
  (role + content_json, plain rendering — no markdown or syntax
  highlighting yet).
- `app/main.py` gains `CORSMiddleware` allowing `http://localhost:5173`
  for local dev.

Done-check:
`cd web && npm run build` exits 0 (type-checks and bundles cleanly),
pasted fresh, in one sitting. (There is no frontend test runner in this
project yet — live browser verification against the real running API,
using the `/run` skill, happens at Gate 2's shipping-proof check, the
same role curl-against-live-uvicorn has played for every backend slice
so far; it is not itself the done-check.)

Out-of-scope:
- Message composing, `POST /api/conversations/{id}/messages`, SSE
  consumption.
- ECharts / chart rendering.
- shadcn/ui component installation.
- A routing library (react-router or similar).
- Docker-compose "web" service wiring, production build config,
  deployment.
- Auth/login screens (F8).
- Dashboard page (F6/M6).
- Any styling polish beyond making the list and detail views readable.
