# Brief — sql-explanation-viewer

Date: 2026-08-06
Milestone: M5 Chat UI — "SQL viewer with explanation"

Goal:
Render `analysis.explanation` and the executed `sql` in a collapsed "View
SQL" section beneath each assistant message, expandable on click, using
data already flowing through `content_json` (no backend change).

Constraints:
- No new dependencies. Follow established frontend conventions: Tailwind
  utility classes inline, plain function components with
  inline-destructured typed props, local component state (no new
  state-management library) — same pattern `ChartView.tsx` and
  `AssistantChart` (`App.tsx`) already use for per-message rendering.
- Collapsed by default; a click reveals both the SQL (in a `<pre>`,
  monospace, matching the existing raw-dump styling already used
  elsewhere in `App.tsx`) and `analysis.explanation` as plain text.
- No backend changes. Do not touch `analyze_answer.py`, `prompts/analyze.md`,
  `AnalyzeResponse`, or any endpoint in `app/main.py`.
- No syntax highlighting for the SQL — plain `<pre>` text, matching the
  existing raw-dump convention (ARCHITECT.md stack: no new frontend deps
  without asking).

Inputs:
- `web/src/api.ts`'s `asAssistantContent()` and `Analysis` interface
  (`{summary, explanation, chart_spec, follow_ups}`) — the exact fields
  already available per message, just not yet rendered beyond
  `chart_spec`.
- `web/src/components/ChartView.tsx` and `web/src/App.tsx`'s
  `AssistantChart` helper (near the message-rendering loop) as the
  established pattern for a small per-message component gated on
  `role === 'assistant'`.
- A real assistant message's full shape (previous handoff's Proof, or any
  row in `app.messages` — e.g. `sql: "SELECT ..."`,
  `analysis.explanation: "The query joined..."`) as ground truth for what's
  actually available to render.

Outputs:
- `web/src/api.ts`: `asAssistantContent()` (or a small sibling accessor)
  exposes `sql` and `analysis.explanation` alongside the existing
  `rows`/`chartSpec`.
- New `web/src/components/SqlDetails.tsx` (or equivalent): a collapsed-by-
  default `<details>`/toggle-button section showing the SQL and
  explanation for one assistant message.
- `web/src/App.tsx`'s message loop renders it alongside `ChartView` and the
  existing raw JSON dump — nothing removed.

Done-check:
Start the dev server (`docker compose up` or `npm run dev` + the API), ask
a real question through the chat UI, screenshot (via Playwright) the
message showing the section collapsed by default, then click to expand it
and screenshot showing the real SQL and explanation text revealed.

Out-of-scope:
- Follow-up chips (`analysis.follow_ups` rendered as clickable buttons
  that populate the compose input) — separate next-next slice.
- Any chart-rendering change (`ChartView.tsx` stays as-is).
- Any backend change.
- Syntax highlighting for the SQL.
