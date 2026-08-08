# Handoff

Date: 2026-08-08
Slice just completed: plans/briefs/2026-08-08-dashboard-strictmode-fetch-guard.md
  + plans/logs/2026-08-08-dashboard-strictmode-fetch-guard.md
  (commit b0ab678, capture 7237854)

## State of the work

- **`web/src/components/DashboardView.tsx`'s mount `useEffect` now guards
  against React 18 StrictMode's dev-only double-invoke**: a local `stale`
  boolean (`false` at the start of each invocation) is checked before
  each of `setDashboard`/`setError`/`setLoading` in
  `.then`/`.catch`/`.finally`, and flipped `true` in the effect's returned
  cleanup function. This mirrors, exactly, the pattern already used by
  `web/src/App.tsx`'s conversation-detail effect (lines 173-194) — now
  the second, independently-verified instance of this pattern in the
  codebase.
- **The flag is named `stale`, not `ignore`** — a deliberate deviation
  from the brief's literal Constraints text (which specified `ignore`,
  citing React's own docs), caught by the no-slop review's first pass:
  shipping `ignore` would have left the identical concept named two
  different ways in the same codebase (`App.tsx` already uses `stale`).
  Presented to and accepted by the user at Gate 2.
- **No other part of `DashboardView.tsx` touched** — the action handlers
  (delete/rerun/rename/drag) and `actionError` are unrelated to this race
  and were confirmed unaffected by both the diff and the drag-reposition
  shipping proof re-run against the final code.
- **New tests added to `web/tests/DashboardView.test.tsx`, still cannot
  execute** (same standing gap, no vitest/jsdom wired into
  `web/package.json` yet): three new cases proving (1) a stale
  `fetchDashboard` resolution landing after cleanup doesn't render, (2) a
  stale rejection landing after cleanup doesn't surface as an error, (3)
  a stale resolution landing *before* the fresh one settles — while the
  fresh call is still pending — doesn't prematurely clear the loading
  indicator or render stale data (this third case is what actually proves
  the `setLoading` guard matters; the no-slop review's first pass caught
  that the original two cases alone couldn't distinguish guarded from
  unguarded `finally` behavior). Plus two regression cases proving the
  normal single-invocation loading→loaded and loading→error paths are
  completely unaffected.
- **No-slop review, two passes** (record:
  `artifacts/reviews/2026-08-08-dashboard-strictmode-fetch-guard.md`).
  Pass 1 found and fixed: the `ignore`→`stale` naming inconsistency; an
  incidental unrelated reword of a pre-existing test comment (about the
  Rename button's card-merge semantics) that had been smuggled in by the
  test-writer agent, reverted byte-for-byte; the `setLoading`-guard test
  gap described above. Pass 2 found and fixed: a test-file header comment
  that narrated the session's TDD sequencing ("written BEFORE the fix
  lands...") rather than describing current behavior, reworded to present
  tense. Pass 2 clean on every remaining checklist category. Zero
  unresolved findings at commit time.
- **Discovered, NOT fixed (now the next slice): `App.tsx`'s
  conversations-list mount effect** (`web/src/App.tsx:164-171`) has the
  *identical* unguarded StrictMode double-invoke race this slice just
  fixed in `DashboardView.tsx` — same missing guard, same fix shape.
  Found while confirming (per this brief's Out-of-scope) that no other
  effect in `DashboardView.tsx` itself had the issue; `App.tsx` is a
  different file, so fixing it there was correctly out of this slice's
  scope, but it's now a fully-diagnosed, next-smallest slice.
- **A skipped handoff commit from the prior session was closed out**:
  `HANDOFF.md` and `plans/logs/_auto-capture.md` had uncommitted content
  from the end of the drag-reposition slice (that slice's own handoff,
  written hot but never committed). Committed separately as `982f6d7`
  ("Handoff: drag-reposition slice done...") before this slice's own
  commit, to keep the two changes distinguishable in history.
- **No backend, schema, or dependency changes.**

## Proof

```
$ cd web && npm run build
> web@0.0.0 build
> tsc -b && vite build

vite v8.2.0 building client environment for production...
✓ 628 modules transformed.
✓ built in 856ms
```
Real-server shipping proof (dev servers already running from a prior
session, reused directly). Playwright (scratchpad-installed, not added to
`web/package.json`) dragging "Race proof Second" onto "Race proof
First"'s slot, immediately after page load with no settle-wait (the
opposite of the prior slice's workaround — this slice's whole point is
that no settle-wait should be needed anymore):

Pre-fix repro (code temporarily reverted via `git stash` to confirm the
bug is real before trusting the fix):
```json
{
  "headingsBeforeDrag": ["Race proof First", "Race proof Second"],
  "headingsRightAfterDrop": ["Race proof Second", "Race proof First"],
  "headingsAfter6sWait": ["Race proof First", "Race proof Second"],
  "consoleErrors": []
}
```
Reorder visibly reverts after ~6s — bug reproduced.

Post-fix confirmation (final code, fresh proof cards, after all no-slop
fixes):
```json
{
  "headingsBeforeDrag": ["Race proof First", "Race proof Second"],
  "headingsRightAfterDrop": ["Race proof Second", "Race proof First"],
  "headingsAfter6sWait": ["Race proof Second", "Race proof First"],
  "consoleErrors": []
}
```
Reorder survives the full 6-second wait — no revert, zero console errors
on either run. Proof cards deleted afterward both rounds; dashboard 1
reconfirmed back to its baseline 7 pre-existing cards each time.

## Open questions / known issues

- Carried over, unchanged from the previous handoff (still true, still
  unaddressed):
  - Frontend unit tests still cannot execute — no vitest/jest wired into
    `web/package.json`. Adding one is a new dependency (needs an explicit
    ask per CLAUDE.md).
  - `chart_spec` still has no fixed schema by design
    (`prompts/analyze.md`); `ChartView.tsx`'s alias-resolution approach
    remains the frontend's answer to this.
  - ECharts auto-hides overlapping x-axis category labels under narrow
    container widths — not a bug, unaddressed by design.
  - No charting library styling beyond a single fixed accent color; no
    dark mode; no table-view toggle.
  - Decimal-valued rows still serialize as JSON strings, not numbers, in
    the raw `<pre>` dump (conversations view only).
  - `NullPool` needs re-evaluation under uvicorn's single persistent
    event loop — still flagged in `app/db/session.py`'s own comment.
  - What happens to an already-computed answer when its persistence
    write fails: still a plain 500 / silently truncated SSE stream.
  - `tests/test_seed_idempotency.py`'s own real Postgres deadlock
    (M1-era, unrelated code) remains uninvestigated.
  - Lint/type tooling on the Python side (`ruff`, `mypy`) remains
    unaddressed.
  - A `response.content[0].text`/`ThinkingBlock` bug pattern is fixed
    only in `analyze_answer.py`; `generate_sql.py`, `repair_sql.py`,
    `describe.py` still carry the same fragile assumption.
  - The project's own `.venv` (Python 3.11.15) must be used explicitly
    for backend commands.
  - API base URL is a hardcoded `http://localhost:8000` constant in
    `web/src/api.ts`.
  - `Conversation`'s `user_id` FK to `users` is deliberately omitted —
    `users` doesn't exist yet (F8).
  - `queries` table (PRD §7's fourth `app`-schema table) still doesn't
    exist — not needed until the pipeline-logging slice.
  - Docker Desktop's daemon does not auto-start with this
    machine/session — if a session's done-check fails with a Postgres
    connection refusal on port 5433, start Docker Desktop and run
    `docker compose up -d` before assuming a code regression. (Not
    exercised this session — the API and web dev servers were already
    running from a prior session and were reused directly.)
  - The dev Postgres `dashboards`/`dashboard_cards` tables have
    accumulated leftover proof/test cards from prior sessions' real-
    server shipping proofs (harmless; still 7 pre-existing cards,
    reconfirmed this session; still worth a cleanup pass eventually).
  - A `uvicorn` dev server left running from a prior session (bound on
    port 8000) is still up and was reused for this slice's shipping
    proofs rather than restarted.
  - A `vite` dev server left running from a prior session (bound on port
    5173) is still up and was reused for this slice's shipping proofs
    rather than restarted (its HMR correctly picked up both the
    ignore→stale rename and the git-stash pre-fix/post-fix round-trip
    without a manual restart — reconfirmed working this session).
  - `plans/logs/2026-08-07-run-dashboard-card-endpoint.md` still sits
    untracked in the working tree (a leftover from a session several
    slices back whose capture commit was apparently skipped). Still out
    of every subsequent slice's scope; still worth a deliberate small
    cleanup commit eventually.
  - `get_dashboard`'s `ORDER BY DashboardCard.position` (`app/main.py:380`)
    still has no secondary sort key. Still just an observation, not
    fixed; still worth a secondary `id`/`created_at` tiebreaker if it's
    ever seen to matter.
  - Playwright (transient, per this project's established pattern for
    real-browser proofs) cannot be resolved via `npx -p playwright node
    script.mjs` because `npx -p` doesn't add the package to Node's ESM
    resolution path — a throwaway scratchpad install (from a prior
    session, `pw-drag/`) was reused directly this session, confirming
    that pattern's install persists usably across sessions as long as
    the scratchpad directory itself survives.
  - Native HTML5 drag-and-drop events dispatched synthetically must each
    go in their own round-trip/turn (not fired back-to-back synchronously
    in one script block) to give React's batching a chance to commit
    state between them — reconfirmed working this session via the reused
    `pw-drag/race-proof.mjs` script.
  - The DB-drift-on-partial-`repositionCard`-failure tradeoff from the
    drag-reposition slice remains an accepted, documented known
    limitation — not tracked as a bug to fix.
- New this slice:
  - `App.tsx`'s conversations-list mount effect has the identical
    unguarded StrictMode race — now this handoff's next brief (see
    below). Its sibling effect in the same file (the conversation-detail
    fetch, lines 173-194) already has the correct `stale`-flag guard and
    does NOT need this fix.
  - A skipped handoff commit from the drag-reposition slice was found and
    closed out this session (commit `982f6d7`) — worth checking for at
    the start of a session if `git status` shows unexpected `HANDOFF.md`/
    `plans/logs/_auto-capture.md` modifications before assuming they're
    this session's own in-progress edits.

## Next slice (the brief, written NOW while context is hot)

Goal:
Fix `App.tsx`'s conversations-list mount effect so React 18 StrictMode's
dev-only double-invoke can never let a stale duplicate `fetchConversations`
response overwrite newer state — the same bug class just fixed in
`DashboardView.tsx`, in a different file.

Constraints:
- Touch only `web/src/App.tsx`'s conversations-list `useEffect` (currently
  lines ~164-171) — no backend change, no new dependency, no change to
  any other part of `App.tsx` (the conversation-detail effect at lines
  173-194 already has the correct guard and must not be touched;
  `ConversationList`, `ConversationDetailView`, message-sending, and view
  switching are unrelated to this race and stay untouched).
- Use the exact `stale`-flag pattern already established in this same
  file's conversation-detail effect (lines 173-194) — mirror its shape
  precisely (local `stale` boolean, `false` at the start, checked before
  each of `setConversations`/`setError`/`setLoading` in
  `.then`/`.catch`/`.finally`, flipped `true` in the effect's cleanup).
  This is now the third instance of this exact pattern in the codebase
  (App.tsx's own detail effect, DashboardView.tsx's mount effect); match
  it, don't reinvent a variant.
- Do not switch to `AbortController`.
- No visible behavior change for the normal path: a real mount (in
  production, where StrictMode's double-invoke doesn't happen) must still
  show exactly one loading → loaded (or loading → error) transition,
  identical to today.

Inputs:
- `web/src/App.tsx`'s current conversations-list mount effect:
  ```ts
  useEffect(() => {
    setLoading(true)
    setError(null)
    fetchConversations()
      .then(setConversations)
      .catch((e: unknown) => setError(errorMessage(e)))
      .finally(() => setLoading(false))
  }, [])
  ```
- `web/src/App.tsx`'s own conversation-detail effect (lines 173-194) as
  the exact template to mirror — it already solves this identical problem
  correctly, in the same file.
- `web/src/components/DashboardView.tsx`'s now-fixed mount effect (this
  slice, commit `b0ab678`) as a second precedent, plus its test file
  (`web/tests/DashboardView.test.tsx`'s "StrictMode/rerun fetch guard"
  describe blocks) as the pattern for how to test this without a real
  `<StrictMode>`-wrapped render.
- Note: unlike `DashboardView`'s effect (keyed on a changeable
  `dashboardId` prop, which let tests force a second invocation via a
  prop change), this effect's dependency array is `[]` — it only ever
  re-runs via StrictMode's own double-invoke, not via any prop/state
  change. A unit test proving the guard will need a different mechanism
  to force two overlapping invocations (e.g. unmounting and remounting
  the component between two fetches, or directly testing the effect's
  cleanup-then-late-resolution shape the same way the DashboardView tests
  did, adapted for a no-deps effect) — work this out during implementation
  rather than assuming the exact same test-authoring trick transfers
  unchanged.

Outputs:
- The same effect, with the `stale`-flag guard added exactly as described
  in Constraints.
- New test coverage (no existing `web/tests/App.test.tsx` file exists yet
  — this slice creates one, scoped ONLY to this mount effect's race, not
  a full `App.tsx` test suite) proving: a `fetchConversations` promise
  that resolves or rejects AFTER the effect's cleanup has run does not
  call `setConversations`/`setError`/`setLoading`; the normal
  single-invocation path (fetch resolves, no cleanup in between) is
  completely unaffected. Same standing execution gap as every other
  frontend test in this repo (no vitest/jsdom wired in yet).

Done-check:
`cd web && npm run build` (type-checks and builds cleanly) plus a
real-server shipping proof under the dev server (StrictMode active).
Unlike the `dashboardId`-keyed effect this slice's predecessor fixed,
this effect's `[]` dependency array means the only way to force two
overlapping real invocations is StrictMode's own mount/cleanup/remount —
so the live proof needs a way to make the two duplicate real
`GET /api/conversations` requests return distinguishably different data
(e.g. Playwright route interception: delay the first-fired request's
response past the second's, and have the two responses differ in a
checkable way — such as one reflecting a conversation created via a real
API call in between the two requests firing) and confirm the pre-fix code
ends up displaying the delayed-but-first request's (stale) data while the
fixed code displays the second request's (fresh) data. Confirm no console
errors on either run.

Out-of-scope:
- `App.tsx`'s conversation-detail effect (lines 173-194) — already
  correctly guarded, not touched.
- `ConversationList`, `ConversationDetailView`, message-sending
  (`handleSubmit`), and view-switching (`view`/`setView`) — unrelated to
  this race.
- Switching to `AbortController` — the `stale`-flag pattern is the
  minimal, already-twice-proven fix per this brief's Constraints.
- A full `App.tsx` test suite — the new test file this slice creates is
  scoped only to the mount effect's race, matching this project's
  established one-brief-one-file-of-tests-at-a-time discipline.
- Auditing or fixing this same shape anywhere else in the codebase beyond
  `App.tsx`'s two effects (both already accounted for: one fixed here,
  one already correct) — a repo-wide sweep is its own separate slice if
  ever warranted.
- The orphaned `plans/logs/2026-08-07-run-dashboard-card-endpoint.md`
  cleanup — unrelated file, separate housekeeping slice.
