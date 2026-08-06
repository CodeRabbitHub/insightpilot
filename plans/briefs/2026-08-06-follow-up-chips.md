# Brief — follow-up-chips

Date: 2026-08-06
Milestone: M5 Chat UI — "follow-up chips"

Goal:
Render `analysis.follow_ups` as clickable chip buttons beneath each
assistant message; clicking a chip populates the compose input with that
follow-up's text (does not auto-submit).

Constraints:
- No new dependencies. Follow established frontend conventions: Tailwind
  utility classes inline, plain function components with
  inline-destructured typed props, local component state — same pattern
  `ChartView.tsx`/`SqlDetails.tsx` and `AssistantResult` (`App.tsx`)
  already use for per-message rendering.
- Do not auto-submit on click — the user must still be able to edit the
  populated text and press Send, same as typing it manually. Reuse
  `ConversationDetailView`'s existing `question`/`setQuestion` state
  (`App.tsx`) as the target; do not introduce a second state store for
  the compose input.
- No backend changes. Do not touch `analyze_answer.py`,
  `prompts/analyze.md`, `AnalyzeResponse`, or any endpoint in
  `app/main.py`.
- Render exactly what `analysis.follow_ups` contains — no deduplication,
  no capping the number shown, no reordering.

Inputs:
- `web/src/api.ts`'s `Analysis` interface already declares
  `follow_ups: string[]`; `AssistantContent`/`asAssistantContent()` need
  it added the same way `sql`/`explanation` were added last slice (same
  guard-clause style — `Array.isArray`, consistent with the existing
  `rows` check's looseness on element validation).
- `web/src/components/SqlDetails.tsx` and `App.tsx`'s `AssistantResult`
  helper as the established per-message-component pattern — note
  `AssistantResult` currently only takes `{ message }`; this slice will
  need it (or a caller one level up) to also receive a callback into
  `ConversationDetailView`'s `setQuestion`, since chip clicks must reach
  state that currently lives one component above `AssistantResult`.
- A real assistant message's `analysis.follow_ups` array (previous
  handoff's Proof section, or any row in `app.messages`) as ground truth
  for what's actually available to render.

Outputs:
- `web/src/api.ts`: `AssistantContent` gains `followUps: string[]`.
- New `web/src/components/FollowUpChips.tsx` (or equivalent): renders one
  button per follow-up string; `onSelect(text: string)` prop fires on
  click.
- `web/src/App.tsx`: `AssistantResult` (or its caller) wires
  `FollowUpChips`'s `onSelect` through to `ConversationDetailView`'s
  `setQuestion`.

Done-check:
Start the dev server (`docker compose up` or `npm run dev` + the API),
ask a real question through the chat UI, screenshot the chips rendered
with real follow-up text beneath the message, click one, screenshot the
compose input now populated with that exact text (not yet sent).

Out-of-scope:
- Auto-submitting a follow-up on click.
- Any change to `SqlDetails.tsx` or `ChartView.tsx`.
- Any backend change.
- Deduplicating, capping, or reordering the follow-ups list.
