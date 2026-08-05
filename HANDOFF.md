# Handoff

Date: 2026-08-05
Slice just completed: plans/briefs/2026-08-05-message-composing.md
  + plans/logs/2026-08-05-message-composing.md
  (commits b05c795, a68b74e)

## State of the work
- **The frontend's write path now works end-to-end in a real browser.**
  `web/src/api.ts` gained `postConversationMessage(conversationId,
  question)`: POSTs to `/api/conversations/{id}/messages`, drains the
  endpoint's single-event SSE response (buffers to `done`, then parses the
  one `event:`/`data:` frame), and resolves with `{conversation_id,
  message_id, sql, rows}` or throws (using the backend's `detail` on an
  `event: error`, or a plain status-code message on a non-2xx HTTP
  response).
- **`ConversationDetailView` (`web/src/App.tsx`) gained a compose form** —
  a text input + submit button with its own `question`/`sending`/
  `sendError` state, fully independent of the page's `loading`/`error`
  state. On submit: calls `postConversationMessage`; on success clears the
  input and calls a new `onMessageSent` prop; on failure shows an inline
  error and leaves the question text and the already-rendered conversation
  untouched.
- **`App` gained a `refreshKey` counter** added to the existing detail-fetch
  `useEffect`'s dependency array — `onMessageSent` bumps it to re-trigger
  that same effect (reusing its existing `stale`-flag race guard) rather
  than building a second fetch-and-set path.
- **Gate 2's no-slop pass caught and fixed a real regression**: the
  original render gate (`{!loading && !error && selectedId !== null &&
  selectedConversation && <ConversationDetailView .../>}`) unmounted the
  entire detail view — compose form included — on every post-send refresh,
  because re-triggering the effect flips `loading` back to `true`. That is
  exactly the "must not blank out the already-loaded conversation"
  behavior the brief's own Constraints forbid, just on the success path
  rather than during the send. Fixed: the detail view now renders whenever
  `selectedConversation` is populated, regardless of `loading`
  (`web/src/App.tsx:182`); the page-level "Loading…" text was narrowed to
  `loading && !selectedConversation` so first-load behavior is unchanged.
  Confirmed fixed by direct inspection and by a second no-slop pass.
- **Proven end-to-end twice** (before and after the fix), in a real
  browser via headless Chrome driven directly over the DevTools Protocol
  (chromium-cli/Playwright still unavailable in this environment — same
  workaround as the scaffold slice), against a real uvicorn backend (the
  project's own `.venv`, NOT the shell's default `python`/`uvicorn`, which
  resolved to an unrelated venv missing `sqlalchemy` — worth remembering
  next session) and a real Vite dev server:
  - Success path: a real question got a real streamed answer (96,478
    delivered orders, matching `evals/questions.yaml`'s independently
    verified value for the same question); message count went from 2 to
    4; input cleared; zero console errors.
  - Continuous-mount proof: polled the DOM every 250ms across a full real
    send (13 samples) — form and message list present in every sample,
    the blocking "Loading…" text never appeared once.
  - Failure path: backend process killed, then submitted — inline "Error:
    Failed to fetch" shown, question preserved, message count/form/list
    unchanged across 8s of 300ms-interval polling.
  - All throwaway processes (uvicorn, Vite, headless Chrome) stopped
    afterward; ports confirmed free via `netstat`.
- Full gate record (all five checks green, verdict accept, includes the
  caught-and-fixed regression): artifacts/reviews/2026-08-05-message-composing.md.
- Also this session: rewrote `README.md`, which had been left as the
  generic FDE-starter-kit template describing the kit's own tooling rather
  than InsightPilot itself — it now documents the actual project (purpose,
  pipeline, architecture, key features, accurate setup steps verified
  against the real scripts, usage examples, project structure). Commit
  `2bd3084`.

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
dist/assets/index-BWc6qn3o.css    5.87 kB │ gzip:  1.97 kB
dist/assets/index-BW-TLQ3c.js   144.64 kB │ gzip: 47.22 kB

✓ built in 2.34s
```
Live shipping proof (post-fix, real send, 250ms-interval DOM polling):
```
MESSAGE_COUNT_BEFORE: 6
SAMPLES_TAKEN: 18 (every 250ms)
EVER_UNMOUNTED_FORM_OR_LIST: false
EVER_SHOWED_STANDALONE_LOADING_TEXT: false
FINAL_SAMPLE: {"formPresent":true,"listPresent":true,"messageCount":8,
  "buttonLabel":"Send","loadingTextPresent":false}
```
Live failure-path proof (backend killed, then submit, 300ms-interval polling):
```
MESSAGE_COUNT_BEFORE: 8
EVER_UNMOUNTED: false
FINAL_SAMPLE: {"formPresent":true,"listPresent":true,"messageCount":8,
  "buttonLabel":"Send","errorText":"Error: Failed to fetch",
  "inputValue":"this should fail, backend killed just now"}
```
Full transcripts (including the real streamed answer's SQL/rows and the
before-fix regression evidence) in the gate record.

## Open questions / known issues
- **M5 (Chat UI) has its second slice done: read-only scaffold, then
  message composing (the write/streaming path).** Chart rendering
  (ECharts), the collapsed "View SQL" explanation section, follow-up
  chips, and starter questions are all still unbuilt — and, more
  fundamentally, **the backend's "analyze & respond" step (PRD.md F2 step
  6 / §9 item 4) has never been built**: `app/pipeline/answer.py`'s
  `get_answer()` still returns only `(sql, rows)`; there is no
  `prompts/analyze.md` and no `summary`/`explanation`/`chart_spec`/
  `follow_ups` anywhere in the pipeline yet. This is the next brief below
  — a backend-only slice, deliberately not wired into `get_answer()`/
  `app/main.py`/persistence/frontend yet, matching how `generate_sql.py`
  was originally built and proven standalone before later slices wired it
  into the full pipeline.
- **A render-gate/loading-flag pattern to watch**: this slice's one caught
  regression was a `useEffect` re-trigger (for a background refresh)
  flipping a `loading` flag that a render gate treated as "nothing to
  show yet," unmounting an already-populated view. First occurrence in
  this project — distinct from the scaffold slice's stale-response *race*
  (out-of-order fetches, not a loading-flag/render-gate interaction) — not
  yet promoted to CLAUDE.md/no-slop.md per the ratchet's second-occurrence
  rule, but worth naming explicitly if any future slice adds a background
  refresh to an already-rendered, `loading`-gated view.
- **The project's own `.venv` (Python 3.11.15) must be used explicitly for
  `uvicorn`/backend commands** — this session's shell had a *different*
  default `python`/`uvicorn` on PATH (missing `sqlalchemy` entirely, from
  an unrelated environment) that silently shadowed the project's own
  virtualenv. Any future session running the backend directly (not via
  Docker) should invoke `.venv/Scripts/python.exe -m uvicorn ...`
  explicitly rather than trusting a bare `uvicorn`/`python` on PATH.
- **No frontend test runner exists** — carried over from the scaffold
  slice; live browser verification (via CDP, since chromium-cli/Playwright
  are unavailable here) continues to stand in for it at Gate 2.
- **API base URL is a hardcoded `http://localhost:8000` constant** in
  `web/src/api.ts` — open design debt, revisit only if a later slice needs
  configurable environments.
- **What happens to an already-computed answer when its persistence write
  fails**: unchanged, still a plain 500 for `/api/ask`, a silently
  truncated SSE stream for `/api/ask/stream` and
  `/api/conversations/{id}/messages`. Not yet decided whether this needs a
  real fix.
- **`NullPool` needs re-evaluation** once this pool serves live HTTP
  requests under uvicorn's single persistent event loop — still flagged in
  `app/db/session.py`'s own comment, still not acted on.
- **Real installed Python is 3.11.15** (`.venv`), not the 3.12
  ARCHITECT.md names — carried over, not investigated or acted on.
- **Decimal-valued rows still serialize as JSON strings, not numbers** —
  carried over unchanged, visible in the frontend's raw `content_json`
  rendering.
- **`plans/logs/_auto-capture.md` remains silently uncommitted across
  every commit** (pre-existing workflow gap) — flagged for 10+ commits now
  with no fix proposed.
- `tests/test_seed_idempotency.py`'s own real Postgres deadlock (M1-era,
  unrelated code) remains uninvestigated.
- The doubled-Voyage-call-per-question design cost
  (`app/pipeline/generate_sql.py`) remains unoptimized — accepted,
  documented in code.
- Lint/type tooling on the Python side (`ruff`, `mypy`) remains
  unaddressed, carried over from every prior slice.
- The concurrency-safety pattern (session-scoped advisory locks) is still
  scoped to exactly the two test classes it was originally applied to.
- Starlette's `TestClient` still emits the `httpx2` deprecation warning —
  harmless, not acted on.
- `Conversation`'s `user_id` FK to `users` is deliberately omitted —
  `users` doesn't exist yet (F8).

## Next slice (the brief, written NOW while context is hot)
Goal:
Add a new `analyze_answer(question, sql, rows)` pipeline step (PRD.md F2
step 6 / §9 item 4 — the last unbuilt piece of the text-to-SQL pipeline)
that makes one Claude call with the question, the executed SQL, and a
sample of its result rows, and returns a Pydantic-validated `{summary,
explanation, chart_spec, follow_ups}` object — proven standalone via its
own verify script, deliberately NOT wired into `get_answer()`, `app/main.py`,
message persistence, or the frontend yet.

Constraints:
- No new dependencies; reuse the exact `anthropic`/`pydantic` call pattern
  `app/pipeline/generate_sql.py`'s `call_llm_for_sql()`/`GenerateSqlResponse`
  already establish (one Claude call, JSON parsed via
  `app/catalog/describe.py`'s `extract_json_object`, Pydantic validation
  with exactly one retry, `MAX_RETRIES = 1`, raising loudly — no
  placeholder — if both attempts fail).
- New prompt file `prompts/analyze.md`, `string.Template`-based like
  `generate_sql.md`/`repair_sql.md` — prompts stay versioned repo files,
  never inline strings (ARCHITECT.md).
- The result rows fed into the prompt must be capped to a small sample
  (do not serialize the full up-to-1000-row result into the prompt) —
  exact cap size to propose at Gate 1, informed by PRD F1's existing
  50-row display cap as a reasonable ceiling.
- `chart_spec` is validated only as a present JSON object
  (`dict[str, Any]`) this slice — its concrete chart-type/axis-mapping
  schema is deliberately deferred to whichever future slice actually
  renders it (ECharts); designing that schema now, with no consumer,
  would be speculative.
- `follow_ups` validated as a non-empty list of strings (PRD F1: "3-5
  suggested follow-up questions").
- Exact module path: `app/pipeline/analyze_answer.py`, matching
  `generate_sql.py`/`validate_sql.py`/`execute_sql.py`/`repair_sql.py`'s
  one-file-per-pipeline-step convention.
- Must NOT change `get_answer()`, `app/main.py`, message persistence, or
  any frontend file this slice — wiring is explicitly a later slice's job,
  so this one stays reviewable and its own contract is provable in
  isolation, matching how `generate_sql.py` was originally built and
  proven alone before later slices wired it into the full pipeline.

Inputs:
- PRD.md F2 step 6 and §9 item 4 (`analyze.md`: "question + SQL + result
  sample → JSON: {summary, explanation, chart_spec, follow_ups[]}").
- `app/pipeline/generate_sql.py` (`call_llm_for_sql`, `GenerateSqlResponse`,
  `PROMPT_TEMPLATE`/`PROMPT_FILE`/`DEFAULT_MODEL`/`MAX_RETRIES` convention)
  and `app/catalog/describe.py` (`extract_json_object`) as the patterns to
  mirror exactly.
- `app/pipeline/answer.py`'s `get_answer()` return shape (`sql, rows`) —
  the exact input shape `analyze_answer()` must accept, so a later slice
  can wire `analyze_answer(question, sql, rows)` in directly.

Outputs:
- `prompts/analyze.md`.
- `AnalyzeResponse` Pydantic model: `summary: str`, `explanation: str`,
  `chart_spec: dict[str, Any]`, `follow_ups: list[str]`.
- `app/pipeline/analyze_answer.py`: `analyze_answer(question, sql, rows) ->
  AnalyzeResponse`.
- `app/pipeline/verify_analyze_answer.py`: the done-check script — calls
  the real `get_answer()` for `FIXED_QUESTION` to get a real `(sql, rows)`
  pair (not hand-faked input), passes it to `analyze_answer()`, and
  asserts the result satisfies `AnalyzeResponse` with non-empty
  `summary`/`explanation`/`follow_ups` and a `chart_spec` dict.

Done-check:
`python -m app.pipeline.verify_analyze_answer` exits 0, pasted fresh.

Out-of-scope:
- Wiring `analyze_answer()` into `get_answer()`, `app/main.py`'s response
  models, message persistence, or any frontend rendering (charts,
  follow-up chips, the "View SQL" explanation section) — later slice(s),
  once this step's own contract is proven in isolation.
- Designing `chart_spec`'s concrete schema beyond "a JSON object" —
  deferred to the slice that actually renders it.
- Any change to `evals/questions.yaml`/`evals/run.py` — they test
  `get_answer()`'s SQL-correctness only, and `analyze_answer()` isn't
  wired into that call path yet, so there is nothing for this slice to
  regress or meaningfully extend there.
- `explain_sql.md` (PRD §9 item 5) — a separate prompt/step, not this one.
