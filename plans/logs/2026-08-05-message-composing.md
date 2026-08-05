# Slice log — message-composing

Date: 2026-08-05
Brief: plans/briefs/2026-08-05-message-composing.md

## The plan you approved
A form (text input + submit button) added to `ConversationDetailView`,
with its own local `question`/`sending`/`sendError` state. On submit, a
new `postConversationMessage()` (`web/src/api.ts`) POSTs to
`/api/conversations/{id}/messages` and drains the endpoint's single-event
SSE response; on success the input clears and an `onMessageSent` callback
bumps a `refreshKey` counter on `App` to re-trigger the existing,
`stale`-flag-protected detail-fetch effect — no new fetch-and-set path, no
duplicated race guard, no client-side message construction. Design note:
artifacts/design/2026-08-05-message-composing.md.

## The diff you accepted
Commit `b05c795` — "Add message composing to the conversation detail
view". 5 files changed, 390 insertions(+), 3 deletions(-) (full stat in
`plans/logs/_auto-capture.md`). Gate record (all five checks green,
verdict accept): artifacts/reviews/2026-08-05-message-composing.md.

## The done-check output
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
Shipping proof (real backend + real Vite dev server + headless Chrome
driven over the DevTools Protocol, chromium-cli/Playwright still
unavailable in this environment): a real question ("How many orders have
the status delivered?") got a real streamed answer (`96478`, matching
`evals/questions.yaml`'s independently-verified value for the same
question); message count went 2 → 4, input cleared, zero console errors.
250ms-interval DOM polling across the full send confirmed the form and
message list stayed mounted throughout — no unmount, no blocking
"Loading…" flash. The failure path (backend killed mid-session, then
submit) was verified the same way: inline error shown, question preserved,
message count/form/list unchanged across 8s of polling. Full transcript
in the gate record.

## One thing you rejected or changed
The plan's `refreshKey` mechanism itself was correct and kept as-is (it
reuses the existing effect's `stale`-flag race guard rather than
duplicating it). What had to change was the render gate it fed into: the
plan didn't anticipate that re-triggering the effect would flip `loading`
back to `true`, and the pre-existing gate — `{!loading && !error &&
selectedId !== null && selectedConversation && <ConversationDetailView
.../>}` — would then unmount the entire detail view, compose form
included, on every successful send's refresh. That's precisely the
"sending a second message must not blank out the already-loaded
conversation" behavior the brief's own Constraints forbid — it just
surfaced on the success path instead of during the send itself, and
nothing in the plan named it as an accepted trade-off.

Caught by the no-slop pass (not the plan review, not the initial live
verification — the happy-path browser check by itself didn't reveal it,
since a fast local response makes the unmount-and-remount easy to miss
without polling). Fixed by decoupling the detail view's render condition
from `loading` — it now renders whenever `selectedConversation` is
populated, regardless of an in-flight refresh — and narrowing the
page-level "Loading…" text to `loading && !selectedConversation` so the
true first-load case is unaffected. Re-verified live via 250ms-interval
DOM polling across a real send (13 samples, form/list present in every
one) and a second no-slop pass confirming no new issue.

This is a first occurrence of this specific pattern (a background-refresh
re-triggering a loading flag that a render gate treats as "nothing to
show") — distinct from the scaffold slice's stale-response *race*, which
was about out-of-order fetches, not a loading-flag/render-gate
interaction. Not promoted to CLAUDE.md/no-slop.md yet, per the ratchet's
second-occurrence rule; worth watching for in any future slice that adds
a background refresh to an already-rendered view guarded by a `loading`
flag.

## The next smallest slice
Implement the backend's "analyze & respond" step (PRD.md F2 step 6, still
unbuilt — `app/pipeline/answer.py`'s `get_answer()` currently returns only
`(sql, rows)`, and no `prompts/analyze.md` exists yet): a second LLM call
that takes the question, SQL, and a result sample and returns
`{summary, explanation, chart_spec, follow_ups}` as one Pydantic-validated
JSON object, wired into `get_answer()` and persisted alongside `sql`/
`rows` — still no frontend rendering change this next slice, so the
existing `<pre>`-formatted JSON view simply gains a couple more fields.
Frontend chart rendering (ECharts) becomes the slice after that, once
there's a real `chart_spec` to render.
