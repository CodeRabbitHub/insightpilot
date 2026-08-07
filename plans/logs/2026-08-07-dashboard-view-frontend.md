# Slice log — dashboard-view-frontend

Date: 2026-08-07
Brief: plans/briefs/2026-08-07-dashboard-view-frontend.md

## The plan you approved
`fetchDashboard(id)` + `DashboardDetail`/`DashboardCardWithRows` types
added to `api.ts`, mirroring `fetchConversation`'s throw-on-`!ok` shape;
a new `DashboardView.tsx` fetches on mount and renders one title +
unmodified `ChartView` per pinned card; `App.tsx` gets a
`Conversations`/`Dashboard` nav toggle (local `useState`, no router)
wired to `dashboardId={1}`. No backend change.

## The diff you accepted
Commit `6f04d37` — "Add read-only Dashboard view to the React app". 7
files changed, 653 insertions(+), 21 deletions(-) (full stat in
`plans/logs/_auto-capture.md`). Gate record (all five checks green,
verdict accept): `artifacts/reviews/2026-08-07-dashboard-view-frontend.md`.

## The done-check output
```
$ cd web && npm run build
> web@0.0.0 build
> tsc -b && vite build
✓ 628 modules transformed.
✓ built in 2.96s
```
Live shipping proof (real backend, real Postgres, real Vite dev server,
real headless Chromium via Playwright — installed transiently this
session, not added to `package.json`/lockfile): posted a real dashboard
card (id 1814, "Gate-check proof card: revenue by state", a real
`SUM(oi.price)`-by-`customer_state` query with a matching x/y/bar
`chart_spec_json`) onto dashboard 1, confirmed it executes via
`POST /api/cards/1814/run` (5 real rows: SP/RJ/MG/RS/PR), drove a real
headless browser to the running app, clicked the "Dashboard" nav button,
and confirmed the card's title and rendered ECharts bar chart both appear
— zero console errors. Proof card deleted afterward
(`DELETE /api/cards/1814` → 204).

## One thing you rejected or changed
The first no-slop pass caught two things in the initial diff, both
required fixing before this gate went green:
1. **Duplication**: the first `DashboardView.tsx` draft copy-pasted
   `errorMessage()` verbatim instead of importing it from `api.ts` — both
   files already import from there. Fixed by exporting `errorMessage`
   from `api.ts` and having both files import the shared one.
2. **Filing**: a done-check screenshot PNG had been committed under
   `artifacts/design/`, which (per every prior file in that directory, and
   CLAUDE.md's own taxonomy) holds design mockups, not proof screenshots —
   and no prior slice in this project's history ever committed a
   screenshot at all. Fixed by deleting the file; the visual evidence
   lives in this log and the gate record instead, matching precedent.

Not promoting either to a standing rule yet — first occurrence of both in
this project's logs.

## The next smallest slice
Extract the now-4-times-duplicated `DashboardCard`→`DashboardCardDetail`/
`DashboardCardWithRows` ORM mapping in `app/main.py` into a
`_card_to_detail(card)` helper and use it at all four sites
(`create_dashboard_card`, `get_dashboard`, `patch_dashboard_card`,
`run_dashboard_card`) — flagged in the prior slice's handoff as the
promotion trigger on a 5th occurrence, and the frontend has no more
read-only surface work queued (rename/delete/re-run card actions are the
next real frontend features, one at a time, per the brief's
out-of-scope). This backend cleanup is smaller and safer to land first.
