# Design note — SQL/explanation viewer

Date: 2026-08-06
Slice: plans/briefs/2026-08-06-sql-explanation-viewer.md
Surface: the conversation detail view in `web/` — a collapsed "View SQL"
section beneath each assistant message, alongside the existing chart and
raw JSON dump.

## Who uses this and what are they trying to do

Whoever is driving this slice, checking the query and explanation behind
a charted answer without cluttering the default view — the next concrete
piece of M5's "chart + SQL viewer + follow-up chips."

## The decision

A new `web/src/components/SqlDetails.tsx` takes `sql` and `explanation`
(both now extracted by `asAssistantContent()` in `web/src/api.ts`,
alongside the existing `rows`/`chartSpec`) and renders a native
`<details>/<summary>` element: collapsed by default, expands on click to
show the SQL in a `<pre>` (matching the existing raw-dump's
`overflow-x-auto whitespace-pre-wrap text-sm` styling) and the
explanation as plain text beneath it.

`<details>` was chosen over a `useState`-driven toggle button because it
gives the exact required behavior — collapsed by default, expandable on
click — with zero new state, and the codebase currently has no `useState`
used for pure view-state (every existing instance is data/async-flow),
so this doesn't introduce a new pattern where a simpler native one
already does the job.

`asAssistantContent()` was extended in place (added `sql`/`explanation`
guards, same style as the existing `rows`/`chartSpec` checks) rather than
adding a second accessor, since both new fields land through the same
`content_json` shape-check and a single accessor is simpler to reason
about than two overlapping ones.

## Rejected alternative

A `useState`-driven expand/collapse button, rejected: it would duplicate
what `<details>` gives for free, and the brief's constraint against a new
state-management library extends naturally to not inventing new local
view-state where the native element already covers it.

## Why

Minimal: reuses the exact null-safety pattern (`asAssistantContent`
returning `null` for any message shape that doesn't resolve — including
every pre-`sql`-field legacy message) and the exact `<pre>` styling
already established, so the new section behaves consistently with the
rest of the page without adding new conventions.

## Open design debts

Same as the previous handoff: no syntax highlighting (explicitly
out-of-scope), no dark mode, no shadcn/ui. Follow-up chips remain the
next slice.
