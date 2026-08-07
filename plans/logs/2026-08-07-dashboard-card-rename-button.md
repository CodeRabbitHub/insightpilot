# Slice log — dashboard-card-rename-button

Date: 2026-08-07
Brief: plans/briefs/2026-08-07-dashboard-card-rename-button.md

## The plan you approved
`api.ts` gains `renameCard(id, title)` following the PATCH+JSON-body
pattern; `DashboardView.tsx` gains a Rename button (`text-gray-700`,
between Re-run and Delete) wired to a handler that prompts via
`window.prompt`, no-ops on cancel/empty input, and merges only `title`
from the response into the matching card's state — never swapping the
whole object, since the PATCH response has no `rows` field and would
otherwise blank the chart.

## The diff you accepted
Commit `41c0153` — "Add rename button to pinned dashboard cards" (mechanics
in `plans/logs/_auto-capture.md`). `web/src/api.ts`, `web/src/components/DashboardView.tsx`,
`web/tests/DashboardView.test.tsx`, new `web/tests/api.renameCard.test.ts`,
plus the brief and this slice's gate record
(`artifacts/reviews/2026-08-07-dashboard-card-rename-button.md`).

## The done-check output
```
> web@0.0.0 build
> tsc -b && vite build

vite v8.2.0 building client environment for production...
✓ 628 modules transformed.
✓ built in 2.26s
```
Real-server + real-browser proof (Gate 2 check 5, run against the final
diff): created proof card 2299 via `POST /api/dashboards/1/cards` → real
headless Chromium (Playwright, transient) opened the Dashboard tab,
clicked card 2299's Rename button, auto-accepted the native `window.prompt`
via `page.on('dialog')` → network trace confirmed
`PATCH http://localhost:8000/api/cards/2299` with body
`{"title":"Renamed by Playwright proof v2"}` → 200, `consoleErrors: []`,
8 sibling headings identical before/after, chart canvas still rendered
(rows/chart_spec_json not blanked) → proof card deleted
(`DELETE /api/cards/2299` → 204) → fresh `GET /api/dashboards/1` confirmed
7 cards remain, all pre-existing. Zero DB pollution left by this slice.

## One thing you rejected or changed
The brief's Constraints literally specified a fourth dedicated
`renameError` state, distinct from `error`/`deleteError`/`rerunError`.
The no-slop reviewer's pass 1 flagged that as the third occurrence of an
identical error-state/handler/button shape across delete/rerun/rename —
exactly the checklist's own "third occurrence means extract" trigger, and
the same shape this project already promoted once this session (the
rerun slice's `mockFetchOnce` extraction). I asked the user directly:
keep the brief's literal fourth state, or consolidate all three into one
shared `actionError` + a shared `updateCard(cardId, merge)` helper. User
chose to consolidate — the second time this project has chosen to fix a
third-occurrence duplication inline rather than deferring it. **This
pattern has now repeated twice** (test-helper extraction in the rerun
slice, error-state/handler consolidation here). Promoted per direct
sign-off: `templates/no-slop.md`'s Duplication section gains a new line
("a third occurrence of ANY parallel structure... is extracted in the
same slice that creates it, even when the brief's Constraints spelled
out the un-extracted, brief-literal version"), citing both occurrences.

## The next smallest slice
Drag-to-reposition — the last of the three originally-missing card
actions (Delete, Re-run, Rename now all shipped) — updating each card's
`position` via the already-existing `PATCH /api/cards/{id}` (the
`position` field this slice deliberately left unused).
