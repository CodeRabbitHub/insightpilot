# Brief — dashboard-card-rename-button

Date: 2026-08-07
Milestone: M6 Dashboard (card actions)

Goal:
Add a rename control to each pinned card in `DashboardView.tsx` that calls
the already-shipped `PATCH /api/cards/{id}` (title-only) and updates that
card's title in place on success.

Constraints:
- Frontend only (`web/src/api.ts` + `web/src/components/DashboardView.tsx`)
  — no backend changes; `PATCH /api/cards/{id}` already exists and is
  untouched (`app/main.py:416-437`, `PatchDashboardCardRequest {title?,
  position?}` — this slice only ever sends `title`, never `position`).
- No new dependency (per ARCHITECT.md's excluded-deps list) — no custom
  inline-edit input/modal component; use `window.prompt` (native browser
  API, zero new dependency).
- `web/src/api.ts` gains `renameCard(id: number, title: string): Promise<DashboardCardDetail>`:
  `fetch` with `method: 'PATCH'`, `headers: { 'Content-Type': 'application/json' }`,
  `body: JSON.stringify({ title })`, against `/api/cards/${id}` — throws
  `Error` with route + status on `!response.ok` (mirroring the existing
  throw shape), resolves with the parsed JSON body on success. Note the
  response type is `DashboardCardDetail`, NOT `DashboardCardWithRows` —
  the PATCH route never touches or returns `rows`, so swapping the raw
  response into `dashboard.cards` would silently wipe out that card's
  `rows` and blank its chart. The state update must merge only `title`
  from the response into the existing card object, preserving
  `rows`/`chart_spec_json` untouched.
- UI: add a third button, "Rename" (after Re-run, before Delete, same
  `text-sm ... hover:underline` idiom, pick an accent distinct from both
  blue and red — e.g. `text-gray-700`), that calls
  `window.prompt('New title', card.title)`. If the result is `null` (user
  cancelled) or trims to an empty string, do nothing — no request sent.
  Otherwise call `renameCard(card.id, trimmedTitle)`; on success, merge
  the new title into that one card's state (siblings and that card's own
  `rows`/`chart_spec_json` untouched); on failure, leave the card's title
  unchanged and surface the error via a fourth dedicated state,
  `renameError` — not `error`/`deleteError`/`rerunError` (same
  render-guard reasoning already applied twice this project).
- Match the existing file's style: functional component, `useState`,
  Tailwind utility classes consistent with the file's existing action
  buttons.

Inputs:
- `web/src/components/DashboardView.tsx` (current, post rerun-slice) —
  the `<div className="flex items-center gap-2">` action-button wrapper
  is where a third button goes.
- `web/src/api.ts`'s `runCard` (POST, parsed-JSON-response shape) and
  `deleteCard` (method-only, no-body shape) as the two patterns to
  combine for `renameCard` (PATCH + JSON body + parsed response).
- `app/main.py`'s `patch_dashboard_card` route (`app/main.py:416-437`):
  200 with a `DashboardCardDetail` body (no `rows` field) on success,
  404 `{"detail": "card not found"}` on an unknown id — the contract
  `renameCard` calls against; no backend inspection beyond confirming
  this contract, since the route itself is out of scope.
- `web/tests/DashboardView.test.tsx` and `web/tests/api.runCard.test.ts`
  (existing, as the patterns to mirror), plus the shared
  `web/tests/helpers/mockFetch.ts` fetch-stub helper (reuse it, do not
  redefine `mockFetchOnce` a fourth time).

Outputs:
- `web/src/api.ts` gains `renameCard(id: number, title: string): Promise<DashboardCardDetail>`.
- `web/src/components/DashboardView.tsx`'s per-card action row gains a
  "Rename" button; clicking it prompts for a new title, and on a
  non-empty, non-cancelled input, calls `renameCard` and updates only
  that card's title (preserving its `rows`/`chart_spec_json`), or leaves
  the title unchanged and shows an error on failure.
- Test coverage for: button present per card; prompt is called with the
  card's current title as the default value; cancelling the prompt
  (`null`) or submitting an empty/whitespace string sends no request and
  changes nothing; a successful rename updates only that card's title
  while its `rows`/`chart_spec_json` and all sibling cards are untouched;
  a failed rename leaves the title unchanged and surfaces an error
  without blanking the rest of the list; no extra `fetchDashboard` call
  on any path. (Same standing gap as every prior frontend test file:
  cannot execute this session, no vitest/jest wired in yet.)

Done-check:
`cd web && npm run build` (type-checks + builds cleanly) plus a real-server
shipping proof: create a real pinned card via curl, load the Dashboard tab
in a real browser (Playwright, using `page.on('dialog')` to auto-accept
the native `window.prompt` with a new title since it's a blocking browser
dialog — or manual), click its Rename button, confirm the request hits
`PATCH /api/cards/{id}` with a `{"title": ...}` body and returns 200, the
card's title updates in the DOM while its chart/rows remain rendered (not
blanked), sibling cards are unaffected, and there are no console errors.

Out-of-scope:
- Drag-to-reposition — the last remaining card action; a materially
  bigger effort (needs a drag library or manual pointer-event handling,
  neither of which exists in this codebase yet) and its own future slice.
- A custom inline-edit input/modal component — deliberately using
  `window.prompt` instead, per this brief's Constraints.
- The `position` field of `PatchDashboardCardRequest` — title-only in
  this slice.
- Any backend change to `PATCH /api/cards/{id}` itself.
- The orphaned `plans/logs/2026-08-07-run-dashboard-card-endpoint.md`
  cleanup — unrelated file, separate housekeeping slice.
- Wiring up a frontend test runner (vitest/jest) — a new dependency,
  needs its own explicit ask per CLAUDE.md's standing rules.
