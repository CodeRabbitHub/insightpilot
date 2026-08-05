# Handoff

Date: 2026-08-05
Slice just completed: plans/briefs/2026-08-05-react-vite-scaffold.md
  + plans/logs/2026-08-05-react-vite-scaffold.md
  (commits 21add48, 92bf205)

## State of the work
- **A working frontend now exists at `web/`** — React 18 + Vite +
  TypeScript + Tailwind 3, per ARCHITECT.md's stack decision. One page,
  one component (`App.tsx`), one piece of view state (`selectedId`):
  null shows the conversation list (`GET /api/conversations`), non-null
  shows one conversation's detail (`GET /api/conversations/{id}`) with a
  "← Back" control. Design contract: artifacts/design/2026-08-05-react-vite-scaffold.md.
- **`app/main.py` now has `CORSMiddleware`** scoped to exactly
  `http://localhost:5173` (Vite's dev-server origin) — every existing
  route otherwise byte-for-byte unchanged (confirmed via diff, additions
  only).
- **`web/src/api.ts`** holds `ConversationSummary`/`MessageDetail`/
  `ConversationDetail` TypeScript types mirroring the three backend
  Pydantic models field-for-field, plus `fetchConversations()` /
  `fetchConversation(id)` — thin `fetch()` wrappers, no library. `API_BASE`
  is a hardcoded `http://localhost:8000` constant (open design debt, see
  below).
- **Proven end-to-end in a real browser**: real uvicorn backend + real
  Vite dev server + a real headless Chrome driven over the DevTools
  Protocol directly (chromium-cli and Playwright are both unavailable in
  this environment; drove Chrome's own CDP with a small Node script
  instead — no new dependency installed). List view rendered all 22 real,
  pre-existing conversations, newest-first. A real click loaded
  conversation #155's actual detail: its real question ("What are the top
  5 product categories by number of orders?") and the real generated SQL
  + result rows, rendered as `<pre>`-formatted JSON per message. Zero
  browser console errors. All three throwaway processes (uvicorn, Vite,
  headless Chrome) stopped afterward; `netstat` confirmed all three ports
  free.
- **`npm create vite@latest` defaulted to React 19 and Tailwind v4** —
  caught before the no-slop pass by checking `package.json` right after
  scaffolding. Pinned back to React 18 and Tailwind v3 (with
  postcss+autoprefixer, matching what the brief's Constraints had
  pre-approved by name) to match ARCHITECT.md's actual decision. First
  occurrence of this pattern in the project — no CLAUDE.md/no-slop.md
  promotion yet, but any future slice that runs a scaffolding generator
  should check the generated manifest against ARCHITECT.md before
  building on top of it.
- **No-slop pass fixed five more issues**, all re-verified green: an
  unapproved `oxlint` dependency the Vite template bundled by default
  (removed — not on the brief's dependency allow-list, unused by the
  done-check); a machine-specific hardcoded path in an emergency hook fix
  (see below — now resolved via `git rev-parse --show-toplevel`); an
  unguarded `subprocess.run` call in that same fix (now wrapped in
  try/except matching its neighbor); a stale-response race in the detail
  view (clicking conversation A then B before A's fetch resolves could
  overwrite the view with A's late response — fixed with a
  cleanup-scoped staleness flag); missing `strict: true` in both
  tsconfigs (added; an unsound `catch (e: Error)` became a proper
  `catch (e: unknown)` narrowed via `instanceof Error`).
- **A real, unrelated infrastructure bug was found and fixed this
  session**: running `npm install` inside `web/` shifted the session's
  shared shell cwd, which broke `.claude/settings.json`'s
  PreToolUse/PostToolUse hooks (they invoked `python
  .claude/hooks/*.py` via a relative path) for every subsequent
  Bash/PowerShell call, project-wide, not just for this slice. Fixed:
  hook commands now resolve the repo root via `$(git rev-parse
  --show-toplevel)`; `capture_commit.py`'s own new use of that same git
  call is guarded the same way its neighboring call already was. This
  was flagged explicitly at Gate 2 as an out-of-brief but necessary
  change, not smuggled into the diff.
- Full gate record (all five checks green, verdict accept):
  artifacts/reviews/2026-08-05-react-vite-scaffold.md.

## Proof
```
$ cd web && npm run build

> web@0.0.0 build
> tsc -b && vite build

vite v8.2.0 building client environment for production...
transforming...✓ 16 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.46 kB │ gzip:  0.29 kB
dist/assets/index-D7EbC3tu.css    5.34 kB │ gzip:  1.85 kB
dist/assets/index-DvBiDm5a.js   143.11 kB │ gzip: 46.59 kB

✓ built in 1.11s
```
Live shipping proof (uvicorn + Vite dev server + headless Chrome over
CDP, outside the build check):
```
$ curl -s http://localhost:8000/api/conversations | python -c "..."
22   # real conversations from prior slices' shipping proofs

$ node drive.mjs ws://localhost:9222/devtools/browser/... list.png detail.png
CLICK_RESULT: CLICKED: Untitled | #155 · 8/5/2026, 11:46:21 AM
CONSOLE_ERRORS: []
```
List-view and detail-view screenshots (real data, real click) reviewed
directly this session. Throwaway servers stopped afterward; ports
confirmed free via `netstat`.

## Open questions / known issues
- **M5 (Chat UI) has its first slice done: the scaffold and a read-only
  page.** Message composing, SSE consumption, ECharts rendering, and
  shadcn/ui components are all still unbuilt — see the brief below for
  the next one.
- **No frontend test runner exists** — carried over from this slice's own
  brief; live browser verification (this session, via CDP since
  chromium-cli/Playwright are unavailable here) is standing in for it at
  Gate 2, same as backend shipping proof has always done.
- **`chromium-cli` and Playwright are both unavailable in this
  environment** — this session drove headless Chrome directly over the
  DevTools Protocol with a small one-off Node script instead (using
  Node's built-in global `WebSocket`, no new dependency). Future
  browser-driven shipping proofs in this repo will need the same
  workaround unless one of those tools gets installed — that would be a
  new dependency decision, not to make silently.
- **API base URL is a hardcoded `http://localhost:8000` constant** in
  `web/src/api.ts` — open design debt from this slice's design note,
  revisit only if a later slice needs configurable environments (e.g. a
  real deploy target).
- **What happens to an already-computed answer when its persistence
  write fails**: unchanged, carried over from three slices ago — a plain
  500 for `/api/ask`, a silently truncated SSE stream for
  `/api/ask/stream` and `/api/conversations/{id}/messages`. Not yet
  decided whether this needs a real fix; the next slice's SSE consumption
  will be the first frontend code to actually observe this behavior.
- **`NullPool` needs re-evaluation once this pool serves live HTTP
  requests** under uvicorn's single persistent event loop — still
  flagged in `app/db/session.py`'s own comment, still not acted on.
- **Real installed Python is 3.11.15** (`.venv`), not the 3.12
  ARCHITECT.md names — carried over, not investigated or acted on.
- **Decimal-valued rows still serialize as JSON strings, not numbers** —
  carried over unchanged; the new frontend currently renders
  `content_json` as raw JSON text, so this is visible as-is in the UI
  now, not previously.
- **`plans/logs/_auto-capture.md` remains silently uncommitted across
  every commit** (pre-existing workflow gap) — flagged for 9+ commits
  now with no fix proposed; this session's two commits correctly
  exclude/include it per the established pattern.
- `tests/test_seed_idempotency.py`'s own real Postgres deadlock (M1-era,
  unrelated code) remains uninvestigated.
- The doubled-Voyage-call-per-question design cost
  (`app/pipeline/generate_sql.py`) remains unoptimized — accepted,
  documented in code.
- Lint/type tooling on the Python side (`ruff`, `mypy`) remains
  unaddressed, carried over from every prior slice. The frontend now has
  its own type-checking (`tsc -b` under `strict: true`, part of `npm run
  build`) but no separate linter (this slice's no-slop pass removed the
  Vite template's bundled `oxlint` as an unapproved dependency) — a
  frontend linter, if wanted, is a new-dependency decision for a future
  slice to make explicitly, not a gap to silently fill.
- The concurrency-safety pattern (session-scoped advisory locks) is still
  scoped to exactly the two test classes it was originally applied to.
- Starlette's `TestClient` still emits the `httpx2` deprecation warning —
  harmless, not acted on.
- `Conversation`'s `user_id` FK to `users` is deliberately omitted —
  `users` doesn't exist yet (F8).

## Next slice (the brief, written NOW while context is hot)
Goal:
Wire up message composing into the existing `web/` page: a text input in
the conversation detail view that `POST`s a new question to
`/api/conversations/{id}/messages`, consumes its SSE response, and shows
the new user/assistant messages in the list — proving the write/streaming
path works end-to-end in the browser for the first time, still with
plain (no-chart) rendering.

Constraints:
- No ECharts, no chart rendering — same as the scaffold slice, still
  deferred; the new assistant message's `content_json` renders the same
  `<pre>`-formatted-JSON way every other message already does.
- No shadcn/ui, no routing library — same deferrals as the scaffold
  slice, still not earned.
- No new frontend or backend dependencies. The browser has no native way
  to consume an SSE stream from a `POST` request (`EventSource` is
  GET-only), so this slice hand-rolls a small SSE-frame parser
  (`event: ...\ndata: ...\n\n` blocks) over a `fetch()` `ReadableStream`
  reader in `web/src/api.ts` — a browser API, not a library.
- After a successful send, re-fetch the conversation detail
  (`fetchConversation`, already built) rather than hand-constructing the
  new message objects client-side — the backend is the single source of
  truth for message ids/timestamps, and this avoids a second,
  hand-maintained shape for "a message" in the frontend.
- The compose input's loading/error state must be independent of the
  page's existing detail-load loading/error state — sending a second
  message must not blank out the already-loaded conversation.
- No backend changes — `POST /api/conversations/{id}/messages` and its
  SSE contract are already built and unchanged by this slice.

Inputs:
- `web/src/api.ts` (`fetchConversation`, existing types) and
  `web/src/App.tsx` (`ConversationDetailView`) — where the input and its
  handler are added.
- The existing `POST /api/conversations/{id}/messages` SSE endpoint
  (`app/main.py`, `_conversation_message_stream_events`), unchanged this
  slice: emits exactly one `event: result` (with `conversation_id`,
  `message_id`, `sql`, `rows`) or one `event: error` (with `detail`), then
  closes the stream.
- PRD.md §8's API surface, ARCHITECT.md's SSE-not-WebSockets decision.

Outputs:
- `web/src/api.ts` gains a function that `POST`s a question to
  `/api/conversations/{id}/messages`, reads the `fetch()` response body
  stream, parses out the one `result`/`error` SSE event, and either
  resolves or throws.
- `web/src/App.tsx`'s detail view gains a text input + submit control;
  on submit it calls that function, then re-fetches and re-renders the
  conversation detail on success, or shows an inline error (without
  discarding the already-loaded message list) on failure.

Done-check:
`cd web && npm run build` exits 0, pasted fresh, in one sitting. (Same
role as the scaffold slice: no frontend test runner yet; live
browser verification — typing a real question, watching it stream back,
seeing it persist across a re-fetch — happens at Gate 2's shipping-proof
check via the same CDP-driven approach this session used.)

Out-of-scope:
- ECharts / chart rendering, shadcn/ui components, a routing library —
  all still deferred, same as the scaffold slice.
- Editing or deleting a sent message; retry-on-failure beyond a plain
  error message; multiple conversations open at once.
- Any backend change — the SSE endpoint's contract is fixed input this
  slice.
- Docker-compose "web" service wiring, production build config,
  deployment, auth screens, the dashboard page (F6/M6).
