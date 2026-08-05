# Slice log — chart-view

Date: 2026-08-06
Brief: plans/briefs/2026-08-06-chart-view.md

## The plan you approved
A new `web/src/components/ChartView.tsx` resolves `chart_spec`/`rows`
defensively — recognized bar shape only, real observed key aliases for
both the type discriminator and the x/y field names, nothing fabricated
— and renders one ECharts bar chart or `null`. `web/src/api.ts` gains a
runtime `asAssistantContent()` shape-check plus the `Analysis` type it
needs; `App.tsx` wires it in alongside (not replacing) the existing raw
JSON dump. Design note: artifacts/design/2026-08-06-chart-view.md.

## The diff you accepted
Commit `ac7791a` — "Render analysis.chart_spec as an ECharts bar chart
in the chat UI". 8 files changed, 507 insertions(+) (full stat in
`plans/logs/_auto-capture.md`). Gate record (all five checks green,
verdict accept): artifacts/reviews/2026-08-06-chart-view.md.

## The done-check output
```
$ cd web && npm run build
> web@0.0.0 build
> tsc -b && vite build
vite v8.2.0 building client environment for production...
transforming...✓ 625 modules transformed.
✓ built in 4.79s
```
Live shipping proof (real backend, real Postgres + Anthropic, real Vite
dev server, real headless Chromium via Playwright — installed this
session, `chromium-cli` still unavailable): a fresh conversation
(`POST /api/conversations` → id 391) driven through the actual chat UI.

"What are the top 5 product categories by number of orders?" → real
`chart_spec` (`{"x":"product_category_name","y":"order_count",
"chart_type":"bar",...}`) → a correctly rendered 5-bar chart, all real
category names and counts, screenshot captured.

"How many orders have the status 'delivered'?" → real `chart_spec`
came back as `{"type":"scalar","value":96478,
"value_field":"delivered_order_count"}` — a **fourth** shape never seen
this session, on top of the two named in the brief and the third
(`type`-keyed bar) the first no-slop pass caught. `ChartView` correctly
rendered nothing for it (canvas count stayed at 1, no error, no empty
box) purely because it only ever recognizes `'bar'` — it didn't need to
know what `"scalar"` was to reject it. Zero console errors across both
questions. Vite process stopped after verification, confirmed free via
`netstat`.

## One thing you rejected or changed
The initial `ChartView.tsx` draft checked only `chartSpec.chart_type ===
'bar'`. The first no-slop pass queried the live app DB directly and
found a real, already-persisted message (id 462) using `{"type": "bar",
"x": ..., "y": ...}` instead — the LLM had keyed the exact same
discriminator under a different JSON field name, for the same fixed
question this brief's own done-check uses. This is the same class of
variance the brief already knew about for field names (`x` vs
`x_field`) but hadn't named for the type discriminator itself.

Fixed by extending the same alias-resolution helper (`resolveField()`)
already used for x/y to the type check too:
`resolveField(chartSpec, ['chart_type', 'type'])`. Re-verified by a
second no-slop pass against all 15 real `chart_spec` rows then in the
DB (no false positive on either non-chartable fixture), and this gate's
own live run surfaced yet a fourth shape (`type: "scalar"`) and
confirmed it's still handled correctly by the same strict `=== 'bar'`
check.

Not promoting a standing rule yet — this is the first time this
specific class of "LLM picks a different JSON key for the same
discriminator" showed up as an actual caught-and-fixed defect in a slice
log (the `x`/`x_field` case was handled proactively in the original
design, not caught as a correction). Per the ratchet's second-repetition
threshold, worth promoting to CLAUDE.md/no-slop.md if a *second* logged
correction of this kind appears in a future slice.

## The next smallest slice
The "View SQL"/explanation collapsed section and follow-up chips
(M5's remaining named pieces, explicitly out-of-scope for this slice) —
render `analysis.explanation` behind a toggle and `analysis.follow_ups`
as clickable chips that populate the compose input, using the same
`asAssistantContent()` parsing this slice already added to `api.ts`.
No backend change expected; `sql` and `follow_ups` are already present
in every real `content_json` this slice's own proof observed.
