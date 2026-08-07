# Slice log — dashboard-card-delete-button

Date: 2026-08-07
Brief: plans/briefs/2026-08-07-dashboard-card-delete-button.md

## The plan you approved
`deleteCard(id): Promise<void>` added to `api.ts`, mirroring
`fetchDashboard`'s throw-on-`!ok` shape. `DashboardView.tsx` gets a
`handleDelete` and a per-card "Delete" button: on success, filter the
card out of local `dashboard` state (no refetch); on failure, leave it in
place and surface an error. Standalone button, not the approved mockup's
"⋯" actions dropdown — that shell is deferred to whichever slice adds
Rename, per your explicit choice at planning time.

## The diff you accepted
Commit `39f6331` — "Add delete button to pinned dashboard cards". 6 files
changed, 496 insertions(+), 10 deletions(-):
```
plans/briefs/2026-08-07-dashboard-card-delete-button.md   | 131 +++
artifacts/reviews/2026-08-07-dashboard-card-delete-button.md |  77 ++
web/src/api.ts                                             |   7 +
web/src/components/DashboardView.tsx                       |  44 ++--
web/tests/DashboardView.test.tsx                           | 156 +++-
web/tests/api.deleteCard.test.ts                           |  91 ++
```
Gate record (all five checks green, verdict accept):
`artifacts/reviews/2026-08-07-dashboard-card-delete-button.md`.

## The done-check output
```
$ cd web && npm run build
> web@0.0.0 build
> tsc -b && vite build

vite v8.2.0 building client environment for production...
✓ 628 modules transformed.
✓ built in 824ms
```
Live shipping proof (real backend, real Postgres, real Vite dev server,
real headless Chromium via Playwright — already installed transiently
from a prior session, not in `package.json`/lockfile): posted a real
pinned card (id 2294, "Gate-check proof card: delete button") onto
dashboard 1 via curl, drove a real browser to the running app, clicked
the "Dashboard" nav button, confirmed the card rendered, clicked its
Delete button, confirmed it disappeared from the DOM (0 matching
headings, 0 console errors), then confirmed via a fresh
`GET /api/dashboards/1` that card 2294 was genuinely gone server-side —
not just removed from the DOM.

## One thing you rejected or changed
The first no-slop pass caught a real functional bug, not a style nit:
the brief's own Constraints said to surface delete failures "via the
existing `error` state," but `DashboardView` already had an
`if (error) return <p>...</p>` early-return guard from the initial-fetch
error path. Reusing that state for delete failures meant any failed
delete would blank the *entire* card list and replace it with a single
error paragraph — directly contradicting the brief's "leave the card in
place" requirement, and contradicting the two tests already written for
that exact scenario. Fixed by introducing a separate `deleteError` state
that renders inline above the `<ul>` without an early return, with a
one-line comment explaining why it's not just reusing `error`.

A second, smaller pass then caught that the fix itself was
under-documented: a test-file comment still described the old,
buggy design ("surfaces the error via the existing `error`-state UI"),
and the deviation from the brief's literal wording had no written
justification anywhere in the code. Both fixed with accurate comments
before the diff went green.

First occurrence of this specific pattern (a brief's literal instruction
conflicting with a pre-existing render guard) in this project's logs —
not promoting to a standing rule yet, but worth watching: any future
per-action error state added to an existing component with an
early-return error guard should ask this same question before reusing
that guard's state variable.

## The next smallest slice
Add a re-run button to each pinned card in `DashboardView.tsx` that
calls the already-shipped `POST /api/cards/{id}/run` and refreshes that
card's rows in place (same "leave-siblings-untouched," "no full
`fetchDashboard` refetch," per-action-error-state pattern as this slice
— including the same trap: check whether the initial-fetch `error` guard
would blank the list before reusing it for a re-run failure).
