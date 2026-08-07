# Slice log — dashboard-card-rerun-button

Date: 2026-08-07
Brief: plans/briefs/2026-08-07-dashboard-card-rerun-button.md

## The plan you approved

Mirror the just-shipped delete-button slice's shape exactly: add
`runCard(id)` to `api.ts` (POST, throw-on-`!ok`, parse JSON on success),
add a dedicated `rerunError` state + `handleRerun` to `DashboardView.tsx`
that swaps the matching card by id via `setDashboard`, and a visually
distinct "Re-run" button (blue) alongside Delete (red). Tests written
first from the brief via the test-writer subagent, same conventions as
the existing `deleteCard`/delete-button test coverage.

## The diff you accepted

Commit `a98a53c` — "Add re-run button to pinned dashboard cards".
10 files changed, 603 insertions(+), 42 deletions(-): `api.ts` (+8),
`DashboardView.tsx` (+38/-6), new `api.runCard.test.ts` (106 lines),
`DashboardView.test.tsx` extended (+214), `api.deleteCard.test.ts` and
`api.fetchDashboard.test.ts` refactored (-18/+18 net, see below), new
`web/tests/helpers/mockFetch.ts` (20 lines), plus the brief and gate
record. Full mechanics in `plans/logs/_auto-capture.md`.

## The done-check output

```
> web@0.0.0 build
> tsc -b && vite build

vite v8.2.0 building client environment for production...
✓ 628 modules transformed.
✓ built in 3.52s
```

Real-server shipping proof (full detail in
`artifacts/reviews/2026-08-07-dashboard-card-rerun-button.md`): created a
real pinned card via curl, drove real headless Chromium to the running
Vite dev server, clicked its Re-run button, confirmed
`POST /api/cards/{id}/run` → 200 via network trace, zero console errors,
sibling cards' DOM unchanged, no extra `fetchDashboard` call. Proof card
deleted afterward — verified 7 cards remain, all pre-existing pollution,
zero new pollution from this slice.

## One thing you rejected or changed

Two real no-slop findings, both fixed before the gate went green:
1. **Duplication**: the new `api.runCard.test.ts` was the *third* copy of
   an identical `mockFetchOnce`/`vi.stubGlobal`/`afterEach(unstub)` block
   (already duplicated across `api.fetchDashboard.test.ts` and
   `api.deleteCard.test.ts`). Extracted to `web/tests/helpers/mockFetch.ts`;
   all three files now import it instead of redefining it.
2. **Consistency**: the new button wrapper used `gap-4`, breaking from
   the project's existing `gap-2` convention everywhere else
   (`App.tsx`, `FollowUpChips.tsx`). Changed to `gap-2`.
A third, cosmetic finding on the second no-slop pass (the new helper's
comment named its three current callers by file, which would go stale on
a fourth) was also fixed — reworded to describe the guaranteed property
instead.

This is a genuinely new pattern (first "third-copy" duplication caught in
this project's test files), not a repeat of a previously-logged issue —
no promotion to CLAUDE.md/no-slop.md proposed this slice.

No LLM/prompt/retrieval behavior touched — no eval update needed.

## The next smallest slice

Rename input: add an inline (or click-to-edit) title-rename control to
each pinned card, calling the existing `PATCH /api/cards/{id}` route
(`app/main.py`'s `rename_dashboard_card`, already shipped, title-only
mutation) — the last simple, well-specified remaining card action before
drag-to-reposition, which is a materially bigger UI problem (needs a
drag library or manual pointer-event handling, neither of which exists
in this codebase yet).
