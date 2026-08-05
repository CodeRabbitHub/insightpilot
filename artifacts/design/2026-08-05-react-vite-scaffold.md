# Design note — conversations list/detail page

Date: 2026-08-05
Slice: plans/briefs/2026-08-05-react-vite-scaffold.md
Surface: the one page in the new `web/` frontend — a browser tab hitting
the Vite dev server.

## Who uses this and what are they trying to do
Whoever is driving this slice, proving the frontend toolchain and the
read-only conversation API work together in a real browser for the first
time — not an end user yet. The page needs to be legibly readable, not
polished.

## The decision
One component, one piece of state (`selectedId: number | null`).
- `selectedId === null` → **list view**: fetch `GET /api/conversations` on
  mount; render each as a row (`id`, `title ?? "Untitled"`, formatted
  `created_at`); clicking a row sets `selectedId`.
- `selectedId !== null` → **detail view**: fetch `GET
  /api/conversations/{id}`; render a "← Back" control (clears
  `selectedId`), then the conversation header, then its messages in
  order. Each message renders as a role badge + `<pre>{JSON.stringify(
  content_json, null, 2)}</pre>` — uniform for both `user` and
  `assistant` roles, since the brief explicitly excludes
  markdown/syntax-highlighting/role-specific formatting this slice.
- Minimal Tailwind utility classes for spacing/legibility only. A
  "Loading…" string and a plain error message on fetch failure are
  included as baseline functionality (an unhandled blank screen isn't
  "readable"), not styling polish.

## Rejected alternative
A split-pane (list + detail side by side). Rejected because the brief's
own wording — "switch between list and detail views" — describes a
toggle, and a split-pane is exactly the kind of layout polish the brief
defers; the single-view toggle is also the simpler build.

## Why
Boring and standard; matches ARCHITECT.md's stack decision exactly.
`<pre>`-formatted JSON is the one rendering that's honestly correct for
both message shapes: a table would need to assume `rows` is always
tabular, which `content_json` doesn't guarantee (`{"question": ...}` for
user messages vs. `{"sql": ..., "rows": [...]}` for assistant messages).
Nothing here is a new architectural commitment — it's the minimum that
proves the toolchain works.

## Open design debts
No route-based deep-linking to a conversation (no router this slice, per
Constraints). API base URL is a hardcoded `http://localhost:8000`
constant (matches uvicorn's default dev port) — revisit only if a later
slice needs configurable environments.
