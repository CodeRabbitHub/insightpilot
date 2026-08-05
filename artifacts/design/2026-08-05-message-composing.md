# Design note — message composing

Date: 2026-08-05
Slice: plans/briefs/2026-08-05-message-composing.md
Surface: the conversation detail view in `web/`, added to the existing
read-only page from the scaffold slice.

## Who uses this and what are they trying to do
Whoever is driving this slice, proving the write/streaming path (compose a
question, get a real streamed answer, see it persist) works end-to-end in
a real browser for the first time — same "prove the toolchain" bar as the
scaffold slice, not a polished chat product yet.

## The decision
A `<form>` (text input + submit button) rendered below the existing
message list inside `ConversationDetailView`. Its `question`/`sending`/
`sendError` state lives entirely inside `ConversationDetailView`, not in
`App` — structurally independent of the page-level `loading`/`error`
state, per the brief's constraint that sending a message must not blank
out the already-loaded conversation.

On submit: POST via a new `postConversationMessage` (`web/src/api.ts`),
which drains the endpoint's single-event SSE response and resolves or
throws. On success: clear the input, call an `onMessageSent` callback that
bumps a `refreshKey` counter on `App`, re-triggering the *existing*
detail-fetch `useEffect` (same `stale`-flag-protected fetch already used
for the initial GET-on-select) — no new fetch-and-set code path, no
duplicated race guard. On failure: show an inline error under the form;
the question text and the already-rendered conversation are left
untouched, so the user can retry without retyping or losing context.

## Rejected alternative
Hand-constructing the new user/assistant message objects client-side to
update state immediately, instead of re-fetching. Rejected per the brief:
the backend is the single source of truth for message ids/timestamps, and
a client-side shape would need its own reconciliation logic once the real
re-fetch inevitably lands anyway — building it now is pure waste.

A second rejected alternative: factoring the fetch-and-set logic out of
the `useEffect` into a plain callable function, so both the initial load
and the post-send refresh call it directly. Rejected because that would
need its own guard against the user switching conversations mid-fetch,
duplicating (or replacing with a ref-based scheme) the `stale`-flag
pattern the effect already has. Bumping a counter in the effect's
dependency array reuses that exact guard for free.

## Why
Minimal diff over the scaffold slice's existing structure; no new
architectural commitment. The one browser-API subtlety — the endpoint
emits at most one SSE event then closes, so `postConversationMessage`
drains the whole stream before parsing rather than incrementally
detecting a `"\n\n"` frame boundary — is documented as a comment at the
call site (`web/src/api.ts`) since it's a hidden constraint (relies on the
backend's documented single-event contract) future readers need to know,
not a restatement of what the code does.

## Open design debts
Same as the scaffold slice: no chart rendering, no shadcn/ui, no routing
library — all still deferred. Switching conversations while a send is in
flight is out of scope (see the brief's Out-of-scope); it degrades safely
rather than corrupting state (an in-flight send's eventual result/error
just triggers a refetch of whichever conversation is then selected).
