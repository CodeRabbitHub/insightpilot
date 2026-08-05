# Design note — chart view

Date: 2026-08-06
Slice: plans/briefs/2026-08-06-chart-view.md
Surface: the conversation detail view in `web/` — a bar chart rendered
beneath each chartable assistant message, alongside the existing raw JSON
dump.

## Who uses this and what are they trying to do

Whoever is driving this slice, proving the first real chart renders from
real backend data (not a mock `chart_spec`) — the milestone this slice
starts, M5's "chart + SQL viewer + follow-up chips."

## The decision

A new `web/src/components/ChartView.tsx` takes `chartSpec` and `rows`
(already parsed out of a message's `content_json` by a small runtime
shape-check, `asAssistantContent()` in `web/src/api.ts`) and renders one
ECharts bar chart via `echarts-for-react`, or nothing at all.

Because `chart_spec` has no fixed schema (`prompts/analyze.md` asks the
LLM for "a JSON object... no fixed schema required"), the component
resolves the real shapes actually observed in production for the type
discriminator (`chart_type` OR `type`, both seen keying the same `"bar"`
value across real runs of the same fixed question) and the field names
(`x`/`y` OR `x_field`/`y_field`), and falls back to rendering nothing —
never an error, never a guessed axis — for anything else, including the
non-chartable shapes already observed (`{"chart_type":"none",...}` and
`{}`).

The no-slop pass caught that the initial draft only checked `chart_type`,
missing a real, already-persisted `{"type": "bar", "x": ..., "y": ...}`
run for the exact question named in this brief's own done-check
(message id 462 in the live app DB) — confirmed independently by querying
the DB directly (`app/db/session.py`'s session factory, `Message` model),
not just trusting the review's claim. Fixed by resolving the type
discriminator the same way the field names already were (first non-blank
match across the observed key aliases), rather than trusting one key
name. This is the second occurrence of this exact class of variance
(the LLM choosing a different JSON key for the same real field across
runs) — first was `x`/`x_field`, this is `chart_type`/`type` — worth
watching for a third before promoting a rule to CLAUDE.md/no-slop.md.

Styling: a single fixed accent (`#2a78d6`, the reference palette's
series-1 blue) since this is always a single-series chart; rounded bar
caps, hairline muted gridlines, and a built-in axis tooltip. No legend
(one series, title already names it), no dark mode (nothing else in this
app has one), no separate table view (the existing raw JSON `<pre>` dump,
kept as-is, already covers that).

## Rejected alternative

A stricter `chart_spec` schema enforced client-side (e.g. a Zod parser
requiring one canonical field-name set), rejected because the brief
explicitly defers schema-tightening to a future slice and forbids
touching `analyze_answer.py`/`prompts/analyze.md` this slice — the
frontend has to cope with the real variance, not police it away.

Handling an `orientation: "horizontal"` branch, rejected: never observed
in real output; the brief's Out-of-scope forbids speculative support for
unobserved shapes, and a plain category-x/value-y bar already matches
every real fixture (`orientation: "vertical"`).

## Why

Minimal, defensive-by-construction: the component only ever renders a
shape it has concretely seen work, and silently no-ops otherwise. That
matches the brief's core constraint better than any attempt to "support"
more shapes speculatively.

## Open design debts

Same as every prior frontend slice: no shadcn/ui, no dark mode, no
routing library. Chart types other than bar (line/pie/table) are
deferred until real output actually produces one. `chart_spec`'s lack of
a fixed schema remains open (tracked in HANDOFF.md), this slice only
copes with it in the renderer.
