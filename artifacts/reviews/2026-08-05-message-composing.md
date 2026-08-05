# Review gate — message-composing

Date: 2026-08-05
Brief: plans/briefs/2026-08-05-message-composing.md
Diff reviewed: working tree diff (uncommitted at gate time) —
`web/src/api.ts`, `web/src/App.tsx`

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review
`git diff --stat`:
```
plans/logs/_auto-capture.md | 36 +++++++++++++++++++++++++++++
web/src/App.tsx             | 53 +++++++++++++++++++++++++++++++++++++++---
web/src/api.ts              | 56 +++++++++++++++++++++++++++++++++++++++++++++
3 files changed, 142 insertions(+), 3 deletions(-)
```
`_auto-capture.md` is the pre-existing, unrelated hook log (not part of
this slice's file changes — flagged, not reviewed, same as every prior
slice's log). The two real source files (App.tsx, api.ts) total ~106 net
lines, read in full during the gate. PASS.

## 2. The stated goal matches the actual change
Brief's Goal: wire up message composing — a text input in the conversation
detail view that POSTs a new question to `/api/conversations/{id}/messages`,
consumes its SSE response, and shows the new user/assistant messages,
proving the write/streaming path end-to-end in the browser.

The diff: `postConversationMessage()` (new, in `api.ts`) POSTs the
question and drains/parses the endpoint's single-event SSE response,
resolving or throwing. `ConversationDetailView` (in `App.tsx`) gains a
form with local `question`/`sending`/`sendError` state; on submit it calls
the new function, clears the input and triggers a refresh on success, or
shows an inline error on failure. `App` gains a `refreshKey` counter wired
into the existing detail-fetch effect to perform that refresh (reusing
the effect's existing `stale`-flag race guard rather than duplicating it).

The only change beyond the brief's Outputs is a fix to the render gate
around `ConversationDetailView` (see "Rejected or changed" below) — not an
added feature, but a correction required to actually satisfy a constraint
already written into the brief. No missing behavior, no unrelated
"improvements." PASS.

## 3. The eval or test passed
Done-check (`cd web && npm run build`), run fresh at gate time:
```
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
Exit 0. No backend/prompt change this slice, so `evals/run` is not
applicable (LLM behavior untouched). PASS.

## 4. The no-slop review found no unresolved issues
First pass (before the fix) found one real issue: bumping `refreshKey`
re-ran the conversation-detail `useEffect`, which sets `loading = true`;
the render gate `{!loading && !error && selectedId !== null &&
selectedConversation && <ConversationDetailView .../>}` then unmounted the
entire detail view — including the compose form itself — on every
successful send's refresh. That is exactly the "must not blank out the
already-loaded conversation" behavior the brief's Constraints forbid, just
triggered by the success path instead of the send itself, and it wasn't
written down anywhere as an accepted trade-off.

Fix applied: the detail view's render condition no longer depends on
`!loading` — it renders whenever `selectedConversation` is populated,
regardless of an in-flight refresh (`web/src/App.tsx:182`). The
page-level "Loading…" text was narrowed to `loading && !selectedConversation`
so the very first load (before any conversation is ever fetched) is
unaffected.

Second pass (after the fix), re-run against the corrected diff: confirmed
by direct inspection that the render condition no longer includes
`!loading`; traced initial-load, first-select, post-send-refresh, and
Back-navigation paths, all correct; no new issue introduced. No other
findings in either pass beyond the one above. Zero unresolved findings.
PASS.

## 5. The shipping proof is attached
Real backend (project `.venv`, real Anthropic + Postgres) + real Vite dev
server + real headless Chrome driven directly over the DevTools Protocol
(chromium-cli/Playwright unavailable in this environment, same workaround
as the scaffold slice).

**Success path** — typed "How many orders have the status delivered?"
into an existing conversation (#169, 2 pre-existing messages), submitted:
```
CLICK_RESULT: CLICKED: Untitled | #169 · 8/5/2026, 12:14:04 PM
MESSAGE_COUNT_BEFORE: 2
SENDING_LABEL_IMMEDIATELY_AFTER_SUBMIT: Sending…
FINAL_BUTTON_LABEL: Send (waited 5000 ms)
MESSAGE_COUNT_AFTER: 4
INPUT_VALUE_AFTER: ""
CONSOLE_ERRORS: []
```
The real assistant answer (`SELECT COUNT(*) ... WHERE order_status =
'delivered'` → `96478`) matches the independently-verified value in
`evals/questions.yaml` for the same question. Confirmed via DOM text dump
and a full-page screenshot (both new messages rendered correctly, in
order, under the pre-existing two).

**Continuous-mount proof (post-fix)** — polled the DOM every 250ms across
a full real send (13 samples, ~3.25s): `formPresent`/`listPresent` were
`true` in every sample, the standalone "Loading…" text never appeared
once, `buttonLabel` transitioned `Sending…` → `Send` only once the
message count actually increased.

**Failure path** — backend process killed, then submitted a question
against the already-loaded detail view:
```
MESSAGE_COUNT_BEFORE: 8
EVER_UNMOUNTED: false
FINAL_SAMPLE: {"formPresent":true,"listPresent":true,"messageCount":8,
  "buttonLabel":"Send","errorText":"Error: Failed to fetch",
  "inputValue":"this should fail, backend killed just now"}
```
Inline error shown, question preserved for retry, message count and
form/list presence unchanged throughout (polled every 300ms across 8s) —
confirms the brief's constraint holds on the failure path too, not just
the success path.

Zero browser console errors in any run. All throwaway processes (uvicorn,
Vite, headless Chrome) stopped afterward; ports confirmed free via
`netstat`.

## Rejected or changed
The plan's `refreshKey` mechanism itself was correct and kept as designed
(reuses the existing `stale`-flag-protected effect, no duplicated fetch
path). What changed from the plan was the render gate it fed into: the
plan didn't anticipate that re-triggering the effect would flip `loading`
true and, combined with the pre-existing `!loading` guard, unmount the
detail view on every refresh. Caught by the no-slop pass (not the plan
review), fixed by decoupling the detail view's render condition from
`loading`, and re-verified live (both success and failure paths, via
continuous DOM polling) plus by a second no-slop pass. This is the one
required "at least one thing" for this field.

## Verdict
accept — all five checks green.
