# Brief — message-composing

Date: 2026-08-05
Milestone: M5 Chat UI (PLAN.md) — first message-composing slice; scaffold
(2026-08-05-react-vite-scaffold.md) was the read-only slice before this one.

Goal:
Wire up message composing into the existing `web/` page: a text input in
the conversation detail view that `POST`s a new question to
`/api/conversations/{id}/messages`, consumes its SSE response, and shows
the new user/assistant messages in the list — proving the write/streaming
path works end-to-end in the browser for the first time, still with plain
(no-chart) rendering.

Constraints:
- No ECharts, no chart rendering — same as the scaffold slice, still
  deferred; the new assistant message's `content_json` renders the same
  `<pre>`-formatted-JSON way every other message already does.
- No shadcn/ui, no routing library — same deferrals as the scaffold slice,
  still not earned.
- No new frontend or backend dependencies. The browser has no native way
  to consume an SSE stream from a `POST` request (`EventSource` is
  GET-only), so this slice hand-rolls a small SSE-frame parser
  (`event: ...\ndata: ...\n\n` blocks) over a `fetch()` `ReadableStream`
  reader in `web/src/api.ts` — a browser API, not a library. Consistent
  with ARCHITECT.md's SSE-not-WebSockets decision and its no-new-deps bar.
- After a successful send, re-fetch the conversation detail
  (`fetchConversation`, already built) rather than hand-constructing the
  new message objects client-side — the backend is the single source of
  truth for message ids/timestamps, and this avoids a second,
  hand-maintained shape for "a message" in the frontend.
- The compose input's loading/error state must be independent of the
  page's existing detail-load loading/error state — sending a second
  message must not blank out the already-loaded conversation.
- No backend changes — `POST /api/conversations/{id}/messages` and its SSE
  contract are already built and unchanged by this slice.

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
- `web/src/App.tsx`'s detail view gains a text input + submit control; on
  submit it calls that function, then re-fetches and re-renders the
  conversation detail on success, or shows an inline error (without
  discarding the already-loaded message list) on failure.

Done-check:
`cd web && npm run build` exits 0, pasted fresh, in one sitting. (Same role
as the scaffold slice: no frontend test runner yet; live browser
verification — typing a real question, watching it stream back, seeing it
persist across a re-fetch — happens at Gate 2's shipping-proof check via
the same CDP-driven approach the scaffold slice used.)

Out-of-scope:
- ECharts / chart rendering, shadcn/ui components, a routing library — all
  still deferred, same as the scaffold slice.
- Editing or deleting a sent message; retry-on-failure beyond a plain
  error message; multiple conversations open at once.
- Any backend change — the SSE endpoint's contract is fixed input this
  slice.
- Docker-compose "web" service wiring, production build config,
  deployment, auth screens, the dashboard page (F6/M6).
