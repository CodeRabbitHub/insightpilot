# Review gate — dashboard-view-frontend

Date: 2026-08-07
Brief: plans/briefs/2026-08-07-dashboard-view-frontend.md
Diff reviewed: working tree vs `main` (pre-commit) — `web/src/App.tsx`,
`web/src/api.ts`, `web/src/components/DashboardView.tsx`,
`web/tests/DashboardView.test.tsx`, `web/tests/api.fetchDashboard.test.ts`,
`plans/briefs/2026-08-07-dashboard-view-frontend.md`.

## 1. The diff is small enough to review
6 files changed, 550 insertions(+), 21 deletions(-):
```
plans/briefs/2026-08-07-dashboard-view-frontend.md |  72 ++++++
web/src/App.tsx                                    |  74 ++++--
web/src/api.ts                                     |  31 +++
web/src/components/DashboardView.tsx               |  36 +++
web/tests/DashboardView.test.tsx                   | 262 +++++++++++++++++++
web/tests/api.fetchDashboard.test.ts               |  96 ++++++++
6 files changed, 550 insertions(+), 21 deletions(-)
```
Every line was read directly (not summarized). Pass.

## 2. The stated goal matches the actual change
Goal: "Add a read-only Dashboard view to the React app that fetches
`GET /api/dashboards/1` and renders each pinned card's title and chart."
The diff adds `fetchDashboard`/`DashboardDetail`/`DashboardCardWithRows`
to `api.ts` (mirroring `fetchConversation`'s throw-on-`!ok` shape), a new
`DashboardView.tsx` (fetch-on-mount, per-card title + unmodified
`ChartView`), and an `App.tsx` nav toggle wiring `dashboardId={1}`. No
backend files touched, no router added, `ChartView.tsx` untouched. One
unrequested-but-accepted change: `App.tsx`'s `<h1>` text went from
"InsightPilot conversations" to "InsightPilot" (not in the brief's
Outputs) — reasonable since the header now serves two views, not just
conversations; recorded here as the written exception the checklist
requires rather than left implicit. Pass.

## 3. The eval or test passed
No test runner is wired into `web/package.json` (pre-existing, documented
gap — also true of `SqlDetails.test.tsx`/`FollowUpChips.test.tsx`), so
`web/tests/DashboardView.test.tsx` (15 tests) and
`web/tests/api.fetchDashboard.test.ts` (5 tests), written by the
test-writer subagent from the brief alone, cannot execute this slice
either. Ran the brief's actual done-check fresh instead, twice — once
before and once after the no-slop-driven refactor below, to prove the
refactor changed nothing observable:
```
$ cd web && npm run build
> web@0.0.0 build
> tsc -b && vite build
✓ 628 modules transformed.
✓ built in 2.96s
```
Fresh Playwright run (post-refactor, this gate's own): posted a real
dashboard card (id 1814, "Gate-check proof card: revenue by state",
`SELECT c.customer_state, SUM(oi.price) AS total_revenue FROM
olist.order_items ... GROUP BY c.customer_state ORDER BY total_revenue
DESC LIMIT 5`, `chart_spec_json` with real x/y/chart_type) onto dashboard
1, confirmed it executes via `POST /api/cards/1814/run` (5 real rows:
SP/RJ/MG/RS/PR), started the real Vite dev server + hit the real running
`uvicorn` API, drove headless Chromium (Playwright) to click the
"Dashboard" nav button, and confirmed the card's title and its rendered
ECharts bar chart appear — zero console errors. Card 1814 then deleted
(`DELETE /api/cards/1814` → 204). Pass.

## 4. The no-slop review found no unresolved issues
Two passes by the no-slop-reviewer subagent (read-only). First pass found:
- **Duplication**: `errorMessage()` copy-pasted verbatim into the new
  `DashboardView.tsx` instead of importing it from `api.ts`, which both
  files already import from. **Fixed**: exported `errorMessage` from
  `api.ts`, both `App.tsx` and `DashboardView.tsx` now import it — zero
  duplicate copies.
- **Filing inconsistency**: a done-check screenshot PNG had been placed
  under `artifacts/design/`, which (per CLAUDE.md's own taxonomy and
  every prior file in that directory) holds design mockups, not proof
  screenshots — and no prior slice in this repo's history has ever
  committed a screenshot file at all. **Fixed**: deleted the file; the
  done-check evidence lives in this record and the slice log instead,
  matching precedent.
- The `<h1>` text change (see Check 2) — accepted, not reverted, now
  written down here.

Second pass (post-fix) confirmed both fixes landed cleanly (no orphaned
import, no re-introduced duplicate, nothing staged under
`artifacts/design/`) and found no new issues from the extraction itself.
Zero unresolved findings. Pass.

## 5. The shipping proof is attached
See Check 3 — real backend (Postgres via the existing `uvicorn --reload`
dev server), real Vite dev server, real headless Chromium via Playwright
(installed transiently this session, not added to `package.json`/lockfile
— confirmed via `git status` showing no diff to either), a real posted
card with a real multi-row aggregate query, rendered end-to-end through
the actual new UI path. Pass.

## Rejected or changed
The no-slop pass's duplication finding was **not accepted as-is**: the
first `DashboardView.tsx` draft had its own copy of `errorMessage`;
required extracting it into `api.ts` as a shared export before this gate
could go green. The screenshot-filing finding similarly required deleting
the committed PNG rather than keeping it.

## Verdict
**Accept.** All five checks green.
