# Review gate — chart-view

Date: 2026-08-06
Brief: plans/briefs/2026-08-06-chart-view.md
Diff reviewed: working tree diff (uncommitted at gate time) —
`web/package.json`, `web/package-lock.json`, `web/src/api.ts`,
`web/src/App.tsx`, plus new files `web/src/components/ChartView.tsx`,
`artifacts/design/2026-08-06-chart-view.md`,
`plans/briefs/2026-08-06-chart-view.md`.

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review
`git diff --stat`:
```
plans/logs/_auto-capture.md | 122 ++++++++++++++++++++++++++++++++++++++++++++
web/package-lock.json       |  53 +++++++++++++++++++
web/package.json            |   2 +
web/src/App.tsx             |  10 ++++
web/src/api.ts              |  32 ++++++++++++
5 files changed, 219 insertions(+)
```
`_auto-capture.md` is the pre-existing, unrelated hook log (not part of
this slice's changes, flagged not reviewed, same as every prior slice).
`package-lock.json` is npm-generated, not hand-written. The real
hand-written diff is `App.tsx` (+10), `api.ts` (+32), `package.json` (+2),
plus one new component file (`ChartView.tsx`, 95 lines) read in full.
Total reviewable surface is small. PASS.

## 2. The stated goal matches the actual change
Brief's Goal: render `analysis.chart_spec` as a real ECharts bar chart
beneath each chartable assistant message, using the real `chart_spec`/
`rows` data already flowing through `/api/conversations/{id}/messages`,
defensively treating anything not a recognized bar shape as not
chartable.

The diff: `echarts`+`echarts-for-react` added (pre-approved). `api.ts`
gains `Analysis`, `ConversationMessageResult.analysis`, and
`asAssistantContent()` (a runtime shape-check separating "is this an
assistant answer at all" from `ChartView`'s own bar-specific resolution).
New `ChartView.tsx` resolves `chart_type`/`type` (both real-observed key
names) against `'bar'`, resolves `x`/`x_field` and `y`/`y_field`, coerces
y-values to finite numbers, and renders one ECharts bar chart or `null`.
`App.tsx` wires a new `AssistantChart` helper into the existing message
loop, alongside (not replacing) the raw JSON `<pre>` dump. No backend
file touched; `analyze_answer.py`/`prompts/analyze.md`/`AnalyzeResponse`
untouched. No chart type beyond bar added. No SQL viewer/follow-up chips
work. Matches the brief exactly, no missing behavior, no unrelated
extras. PASS.

## 3. The eval or test passed
No backend/prompt change this slice, so `evals/run` is not applicable.
Frontend has no test runner (consistent with every prior frontend slice),
so the done-check itself is the check, run fresh at gate time — real
build:
```
$ cd web && npm run build
> web@0.0.0 build
> tsc -b && vite build

vite v8.2.0 building client environment for production...
transforming...✓ 625 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                     0.46 kB │ gzip:   0.29 kB
dist/assets/index-D7gtQICa.js   1,282.56 kB │ gzip: 425.02 kB
✓ built in 4.79s
```
Exit 0, no type errors. (The chunk-size warning is expected from adding
ECharts and is not a build failure.) PASS.

## 4. The no-slop review found no unresolved issues
First pass found one real issue: `ChartView.tsx` only checked
`chartSpec.chart_type === 'bar'`, but a real, already-persisted message
in the live app DB (id 462) uses `{"type": "bar", "x": ..., "y": ...}` —
a third real key-naming variant for the same discriminator, same class
as the already-handled `x`/`x_field` variance. Independently confirmed by
querying the live DB directly (not just trusting the subagent's claim):
```
462 {'x': 'product_category_name', 'y': 'order_count', 'type': 'bar',
     'title': 'Top 5 Product Categories by Order Count',
     'orientation': 'vertical'}
```
Fixed by resolving the type discriminator the same way field names
already were — `resolveField(chartSpec, ['chart_type', 'type'])` — rather
than trusting one key name. Design note updated to record this as the
second occurrence of the "LLM picks a different JSON key for the same
field" pattern (ratchet: promote to a standing rule on a third
occurrence).

Second pass, re-run against the fixed diff: confirmed correct against
all 15 real `chart_spec` rows in the live DB (no false positive on either
non-chartable fixture, `{"chart_type":"none",...}` or `{}`; no precedence
issue since no real row carries both `chart_type` and `type`), plus a
fresh live round-trip through the real pipeline. Zero new findings.
PASS.

## 5. The shipping proof is attached
Real backend (already running, real Postgres + real Anthropic calls) +
real Vite dev server, driven by a real headless Chromium via Playwright
(installed this session; `chromium-cli` unavailable, same class of
workaround as every prior frontend slice). A fresh conversation was
created via the real API (`POST /api/conversations` → id 391) and driven
through the actual chat UI, not called directly:

**Chartable question** — "What are the top 5 product categories by
number of orders?", submitted through the real compose form. Real answer
came back (`chart_spec: {"x":"product_category_name","y":"order_count",
"chart_type":"bar",...}`), a `<canvas>` element mounted, and a
full-page screenshot (taken ~1.5s after the second question, so the
mount animation had settled) shows a correctly rendered bar chart with
all 5 categories and their real order counts.

**Non-chartable question** — "How many orders have the status
'delivered'?", submitted in the same conversation. Real answer came back
with a **fourth** real `chart_spec` shape never before observed this
session — `{"type": "scalar", "value": 96478, "value_field":
"delivered_order_count"}` — and `ChartView` correctly rendered nothing
for it: canvas count stayed at 1 (only the first chart), no error, no
empty chart box. This is a stronger proof than the brief's own named
fixtures, since it happened to surface yet another unseen `chart_spec`
shape live and the defensive `=== 'bar'` check handled it correctly
without needing to recognize `"scalar"` specifically.

```
{
  "canvasCountAfterFirst": 1,
  "canvasCountAfterSecond": 1,
  "consoleErrors": []
}
```
Zero browser console errors across both questions. Full-page screenshots
captured for both states (chart present; chart absent). Dev server
process (Vite, port 5173) stopped after verification; confirmed free via
`netstat` (only TIME_WAIT remnants, no active listener). Backend was
already running from before this slice's work and was left as-is (not
started by this gate, not this gate's process to stop).

## Rejected or changed
The initial `ChartView.tsx` draft checked only `chart_type`, missing the
real `type`-keyed bar variant (message 462) — caught by the first
no-slop pass, not the original plan review or the initial build check.
Fixed by extending the same alias-resolution idiom already used for x/y
field names to the type discriminator, and re-verified by a second
no-slop pass plus this gate's own fresh live run (which additionally
surfaced a fourth, previously unseen non-bar shape and confirmed it's
still handled correctly).

## Verdict
accept — all five checks green.
