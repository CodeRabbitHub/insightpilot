# Handoff

Date: 2026-08-05
Slice just completed: plans/briefs/2026-08-05-conversations-read-endpoints.md
  + plans/logs/2026-08-05-conversations-read-endpoints.md
  (commits c7e4700, 41e1e97)

## State of the work
- **`app/main.py` now has PRD.md §8's full conversation CRUD read/write
  surface.** New this slice: `GET /api/conversations` (every
  conversation, newest-first via `created_at DESC, id DESC`, as
  `[{"id", "title", "created_at"}, ...]`) and `GET
  /api/conversations/{id}` (one conversation's detail plus its messages
  in chronological order, as `{"id", "title", "created_at", "messages":
  [{"id", "role", "content_json", "created_at"}, ...]}`, 404 on an
  unknown id). Both are pure reads — no `get_answer()` call, no SSE.
  Three new Pydantic models (`ConversationSummary`, `MessageDetail`,
  `ConversationDetail`) back them, following the existing per-route
  explicit-model convention. `/api/ask`, `/api/ask/stream`, and both
  existing `POST` conversation routes are byte-for-byte unchanged —
  confirmed via diff (additions only).
- **Proven end-to-end with a live uvicorn process + curl**: created an
  empty conversation, confirmed it appeared in the list (newest-first,
  membership by id) and its detail returned `messages: []`; posted a
  real question to it via the existing `POST .../messages` SSE endpoint;
  confirmed the detail endpoint then returned both messages in the
  right order with the right shape; confirmed an unknown sentinel id
  404s. Demo conversation and its messages deleted afterward, confirmed
  gone; throwaway server process stopped and port confirmed free.
- **New test file `tests/test_api_conversations_read.py`** (23 tests, 5
  classes) proves: detail-endpoint shape/order/content exactly, cross-
  checked against a direct DB read (`ConversationDetailTests`); a real
  conversation with zero messages still 200s with an empty list, not a
  404 (`ConversationDetailWithNoMessagesTests` — added mid-slice, see
  below); list-endpoint membership by id, not count, since other
  conversations may exist concurrently (`ConversationListMembershipTests`);
  newest-first relative ordering of two known ids
  (`ConversationListOrderingTests`); unknown-id 404
  (`UnknownConversationIdDetailTests`).
- **Two no-slop findings caught and fixed before merge, both process
  working as designed, not new patterns**: the zero-messages detail case
  was untested (this project's already-promoted "untested edges"
  category, from `2026-08-02-catalog-sync-cli.md`, catching a second
  real instance) — fixed by adding the new test class above; the new
  test file's module docstring was then found stale (didn't mention that
  new class) — fixed.
- Full suite: 268/268 passing at the last full run (247 prior + 21
  read-endpoint tests at that checkpoint; 2 more pure-Python test
  methods were added after with no app-code change).
- `app/db/models.py`, `app/db/session.py`, all migrations, and the
  existing `POST` routes untouched, per this slice's own constraint.

## Proof
```
$ .venv/Scripts/python.exe -m unittest discover -s tests -p "test_api_conversations_read*.py" -v
[... 23 tests across ConversationDetailTests, ConversationDetailWithNoMessagesTests,
     ConversationListMembershipTests, ConversationListOrderingTests,
     UnknownConversationIdDetailTests ...]
----------------------------------------------------------------------
Ran 23 tests in 9.310s

OK
```
```
$ .venv/Scripts/python.exe -m unittest discover -s tests
----------------------------------------------------------------------
Ran 268 tests in 293.800s

OK
```
Live shipping proof (uvicorn + curl, outside the test suite):
```
$ curl -s -X POST http://127.0.0.1:8125/api/conversations
{"id":151}

$ curl -s http://127.0.0.1:8125/api/conversations/151 -w "\nHTTP %{http_code}\n"
{"id":151,"title":null,"created_at":"2026-08-04T22:37:57.374433Z","messages":[]}
HTTP 200

$ curl -s -N -X POST http://127.0.0.1:8125/api/conversations/151/messages \
    -H "Content-Type: application/json" \
    -d '{"question": "How many orders are in the orders table?"}'
event: result
data: {"conversation_id": 151, "message_id": 196, "sql": "SELECT COUNT(*) FROM olist.orders", "rows": [{"count": 99441}]}

$ curl -s http://127.0.0.1:8125/api/conversations/151 -w "\nHTTP %{http_code}\n"
{"id":151,"title":null,"created_at":"2026-08-04T22:37:57.374433Z","messages":[{"id":195,"role":"user","content_json":{"question":"How many orders are in the orders table?"},"created_at":"2026-08-04T22:38:00.773960Z"},{"id":196,"role":"assistant","content_json":{"sql":"SELECT COUNT(*) FROM olist.orders","rows":[{"count":99441}]},"created_at":"2026-08-04T22:38:00.773960Z"}]}
HTTP 200

$ curl -s http://127.0.0.1:8125/api/conversations/999999999 -w "\nHTTP %{http_code}\n"
{"detail":"conversation not found"}
HTTP 404
```
Row cleaned up afterward; confirmed gone. Full gate record:
`artifacts/reviews/2026-08-05-conversations-read-endpoints.md`
(verdict: accept, all five checks green).

## Open questions / known issues
- **M4 (API: FastAPI endpoints, SSE streaming, persistence) is now
  functionally complete** for the conversations surface. Nothing else in
  PRD.md §8's conversation/message routes is missing. Next milestone per
  PLAN.md is M5 (Chat UI) — see brief below. Dashboard/cards endpoints
  (F6/F7's other half) and auth (F8) remain unbuilt but are separate
  milestones, not blockers for M5.
- **No frontend exists yet** — `web/` doesn't exist in this repo. This
  session confirmed `app/main.py` has no CORS middleware configured,
  which the next slice will need to add (scoped to the Vite dev origin
  only) for a browser-based frontend to call these endpoints locally.
- **What happens to an already-computed answer when its persistence
  write fails**: unchanged, carried over from two slices ago — a plain
  500 for `/api/ask`, a silently truncated SSE stream for
  `/api/ask/stream` and `/api/conversations/{id}/messages`. Not yet
  decided whether this needs a real fix.
- **`NullPool` needs re-evaluation once this pool serves live HTTP
  requests** under uvicorn's single persistent event loop — still
  flagged in `app/db/session.py`'s own comment, still not acted on, now
  serving five live endpoints instead of three.
- **Real installed Python is 3.11.15** (`.venv`), not the 3.12
  ARCHITECT.md names — carried over, not investigated or acted on.
- **Decimal-valued rows still serialize as JSON strings, not numbers** —
  carried over unchanged, now also true of both new `GET` endpoints'
  `rows`-containing `content_json` passthrough.
- **`plans/logs/_auto-capture.md` remains silently uncommitted across
  every commit** (pre-existing workflow gap) — flagged for 8+ commits
  now with no fix proposed; each slice's implementation commit and
  capture commit have continued to correctly exclude/include it per the
  established (if imperfect) pattern.
- `tests/test_seed_idempotency.py`'s own real Postgres deadlock (M1-era,
  unrelated code) remains uninvestigated.
- The doubled-Voyage-call-per-question design cost
  (`app/pipeline/generate_sql.py`) remains unoptimized — accepted,
  documented in code.
- Lint/type tooling (`ruff`, `mypy`) and the test runner (`unittest`, not
  `pytest`) remain unaddressed, carried over from every prior slice. The
  next slice adds a *second*, separate toolchain (npm/Vite/TypeScript)
  with its own build command — `npm run build`'s type-checking is not a
  substitute for `mypy` on the Python side.
- The concurrency-safety pattern (session-scoped advisory locks) is still
  scoped to exactly the two test classes it was originally applied to.
- Starlette's `TestClient` still emits the `httpx2` deprecation warning —
  harmless, not acted on.
- `Conversation`'s `user_id` FK to `users` is deliberately omitted —
  `users` doesn't exist yet (F8).

## Next slice (the brief, written NOW while context is hot)
Goal:
Stand up the React 18 + Vite + TypeScript + Tailwind frontend (per
ARCHITECT.md's decision) in a new `web/` directory, with exactly one
page that lists real conversations via `GET /api/conversations` and, on
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
  (this slice, just merged) to call from the browser.
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
