# Handoff

Date: 2026-08-08
Slice just completed: plans/briefs/2026-08-08-app-strictmode-fetch-guard.md
  + plans/logs/2026-08-08-app-strictmode-fetch-guard.md
  (commit df51337, capture a6ecc45)

## State of the work

- **`web/src/App.tsx`'s conversations-list mount `useEffect` now guards
  against React 18 StrictMode's dev-only double-invoke**, the same fix
  shape as `DashboardView.tsx`'s prior slice: a local `stale` boolean
  (`false` at the start of each invocation), checked before each of
  `setConversations`/`setError`/`setLoading` in
  `.then`/`.catch`/`.finally`, flipped `true` in the effect's returned
  cleanup. This mirrors, exactly, this same file's own conversation-detail
  effect (lines 173-194) — now the third instance of this pattern in the
  codebase, all three verified independently.
- **No other part of `App.tsx` touched** — the conversation-detail
  effect, `ConversationList`, `ConversationDetailView`, message-sending,
  and view-switching are unrelated to this race and confirmed untouched
  via `git diff`.
- **New `web/tests/App.test.tsx`** (test-writer subagent, from the brief
  alone), still cannot execute (same standing gap, no vitest/jsdom wired
  into `web/package.json` yet — see this handoff's next brief). Proves,
  via a real `<StrictMode>` wrapper rendered directly in the test
  (matching `web/src/main.tsx`'s actual production wrapping, rather than
  a prop-swap proxy — this effect's `[]` deps give no prop to force a
  second invocation the way `DashboardView`'s `dashboardId` did): (1) a
  stale resolution landing after the double-invoke's cleaned-up first run
  doesn't render; (2) a stale rejection landing after cleanup doesn't
  surface as an error; (3) a stale resolution landing *before* the fresh
  one settles, while the fresh call is still pending, doesn't
  prematurely clear loading or render stale data. Plus two regression
  cases proving the normal (non-StrictMode) single-invocation path is
  unaffected.
- **No-slop review, two passes** (record:
  `artifacts/reviews/2026-08-08-app-strictmode-fetch-guard.md`). Pass 1
  found and fixed: a stale TDD-narration header comment in
  `App.test.tsx` ("written before the fix lands...") — the identical
  defect the immediately-prior slice's own review had caught on the
  sibling `DashboardView.test.tsx`, one commit later, same test-writer
  subagent; and an unexplained defensive mock
  (`fetchConversation`/`postConversationMessage` stubbed but never
  exercised) — fixed with a one-line justification. Pass 2 (fresh,
  against the final diff) confirmed both fixes landed and found nothing
  new. Zero unresolved findings at gate time.
- **Ratchet promotion, by direct sign-off**: the repeated stale-TDD-comment
  defect (2nd occurrence, same subagent) is now a checklist line in
  `templates/no-slop.md` (category 6) AND a direct rule in
  `.claude/agents/test-writer.md` (its own rule #5: write headers in
  present tense, not session TDD-sequencing) — addressing the subagent's
  own habit, not just the catch.
- **Shipping proof, real dev servers + Playwright**: route-intercepted
  `GET /api/conversations` so the first (StrictMode-stale) response
  resolves 2.5s after the second (fresh) response, with distinguishable
  marker payloads. Fixed code: fresh marker shows and survives the late
  stale resolution, zero console errors. Pre-fix repro (`git stash` of
  just the guard): fresh marker gets clobbered by the late stale
  response — bug reproduced for real. Re-confirmed fixed after
  `git stash pop`.
- **A git housekeeping correction happened mid-session**: an early commit
  attempt accidentally bundled this slice's changes into a commit meant
  only for a leftover `plans/logs/_auto-capture.md` entry from the prior
  slice's handoff. Caught before anything was pushed; fixed via
  `git reset --soft HEAD~1` (non-destructive — nothing lost, only the
  commit boundary moved) and re-committed as one accurate commit
  (`df51337`).
- **No backend, schema, or dependency changes.**

## Proof

```
$ cd web && npm run build
> web@0.0.0 build
> tsc -b && vite build

vite v8.2.0 building client environment for production...
✓ 628 modules transformed.
✓ built in 965ms
```

Shipping proof (Playwright, scratchpad-installed `pw-drag/`, reused across
sessions; real `vite`/`uvicorn` dev servers reused from prior sessions):

Fixed code:
```json
{
  "callCount": 2,
  "freshMarkerShownEarly": true,
  "staleMarkerShownEarly": false,
  "freshMarkerAfterWait": true,
  "staleMarkerAfterWait": false,
  "consoleErrors": []
}
```
Pre-fix repro (`git stash push -- web/src/App.tsx`):
```json
{
  "callCount": 2,
  "freshMarkerShownEarly": true,
  "staleMarkerShownEarly": false,
  "freshMarkerAfterWait": false,
  "staleMarkerAfterWait": true,
  "consoleErrors": []
}
```
Post-restore (`git stash pop`) re-run matched the "Fixed code" result
above exactly.

## Open questions / known issues

- Carried over, unchanged from the previous handoff (still true, still
  unaddressed):
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
    `docker compose up -d` before assuming a code regression.
  - The dev Postgres `dashboards`/`dashboard_cards` tables have
    accumulated leftover proof/test cards from prior sessions' real-
    server shipping proofs (harmless; still worth a cleanup pass
    eventually).
  - A `uvicorn` dev server (port 8000) and a `vite` dev server (port
    5173), both left running from prior sessions, are still up and were
    reused again this session for the shipping proof rather than
    restarted.
  - `plans/logs/2026-08-07-run-dashboard-card-endpoint.md` still sits
    untracked in the working tree (a leftover from a session several
    slices back whose capture commit was apparently skipped). Still out
    of every subsequent slice's scope; still worth a deliberate small
    cleanup commit eventually.
  - `get_dashboard`'s `ORDER BY DashboardCard.position` (`app/main.py:380`)
    still has no secondary sort key. Still just an observation, not
    fixed.
  - Playwright (transient, per this project's established pattern for
    real-browser proofs) cannot be resolved via `npx -p playwright node
    script.mjs`; the scratchpad install (`pw-drag/`, under a prior
    session's temp directory) continues to be reused directly and
    continues to persist usably across sessions.
  - The DB-drift-on-partial-`repositionCard`-failure tradeoff from the
    drag-reposition slice remains an accepted, documented known
    limitation — not tracked as a bug to fix.
  - **Frontend unit tests still cannot execute — this is now this
    handoff's own next brief, not an open-ended gap**: `vitest`/jsdom are
    not yet wired into `web/package.json`. Four test files
    (`SqlDetails.test.tsx`, `FollowUpChips.test.tsx`,
    `DashboardView.test.tsx`, `App.test.tsx`) have all been written
    correctly across multiple slices but never executed once — the
    ratchet's 2nd-repetition threshold was exceeded twice over, and the
    user has now explicitly said yes to the new dependency this requires.
- New this slice:
  - A git-history correction (soft-reset + re-commit, see State of the
    work above) happened mid-session — worth remembering that gate-time
    `git add` staging can silently persist across an unrelated commit if
    not cleared, so re-check `git status --porcelain` immediately before
    every commit, not just before starting the gate.
  - `DashboardView.test.tsx`'s own drag-to-reposition tests (not touched
    this slice, but read as precedent) note jsdom's `DragEvent`/
    `DataTransfer` support is unreliable and work around it with a plain
    `Event` + manually-attached `dataTransfer` property. Worth expecting
    similar jsdom friction, and possibly canvas-related friction from
    `echarts-for-react`, when `DashboardView.test.tsx` is actually run
    for the first time under the next slice's new test runner — this is
    exactly why that slice's Out-of-scope defers `DashboardView.test.tsx`
    and `App.test.tsx` execution to a follow-on slice rather than betting
    all four files pass cleanly on the first real run.

## Next slice (the brief, written NOW while context is hot)

Goal:
Wire `vitest` + a jsdom test environment into `web/package.json` as new
devDependencies (explicit user sign-off already given this session) and
get the two simplest existing frontend test files — `SqlDetails.test.tsx`
and `FollowUpChips.test.tsx` — executing and passing for real, as the
project's first actual frontend test run.

Constraints:
- New dependencies are `vitest` and a jsdom environment package (e.g.
  `jsdom` itself, or `@vitest/environment-jsdom` if vitest's own version
  requires it) — nothing else. No `@testing-library` or any other test
  utility library: this project's established house style (all four
  existing test files) renders via `react-dom/client`'s `createRoot` +
  `act` from `react-dom/test-utils` directly, and that style must keep
  working unchanged.
- Vitest gets a jsdom environment via either `vite.config.ts`'s `test`
  block or a new `vitest.config.ts` — implementer's choice, but only one
  of the two, not both.
- A real `npm test` (or equivalently-named) script must exist in
  `web/package.json` and actually invoke vitest against the whole
  `web/tests/` directory.
- Do not modify `SqlDetails.test.tsx`'s or `FollowUpChips.test.tsx`'s
  assertions to make them pass. If a real bug in the component surfaces,
  fix the component; if a test itself turns out to have a genuine defect
  (not just "inconvenient to satisfy"), flag it to the user rather than
  silently loosening it, per CLAUDE.md's standing rule.
- `web/tsconfig.app.json`'s `"include": ["src"]` (which currently excludes
  `web/tests/*.test.tsx` from `tsc -b`'s production type-check) may need a
  companion tsconfig for tests, or vitest's own separate type-checking —
  don't fold test files into the production build's type-check scope
  without flagging that as a deliberate Constraint decision at Gate 1.

Inputs:
- `web/package.json`'s current `devDependencies` (vite, typescript,
  @vitejs/plugin-react, tailwind toolchain — no test runner yet).
- `web/tests/SqlDetails.test.tsx` and `web/tests/FollowUpChips.test.tsx`
  (126 and 135 lines respectively) as the two files this slice must get
  green — both are simpler than the other two existing test files (no
  `vi.mock` module factories, no drag events, no canvas-rendering
  components).
- `web/tests/DashboardView.test.tsx` and `web/tests/App.test.tsx` exist
  but are explicitly NOT this slice's responsibility to get passing (see
  Out-of-scope) — their own header comments already flag jsdom
  `DragEvent`/`DataTransfer` unreliability and canvas quirks that are
  likely to need their own dedicated debugging slice(s) once actually run.

Outputs:
- `web/package.json` with `vitest` + jsdom environment as new
  devDependencies and a working test script.
- A vitest config (wherever it lives) configured for the jsdom
  environment.
- `SqlDetails.test.tsx` and `FollowUpChips.test.tsx` both passing, for
  real, with the actual terminal output to prove it.

Done-check:
`cd web && npm test` (or whatever the final script name is) runs to
completion, exit code 0, with output showing every test in
`SqlDetails.test.tsx` and `FollowUpChips.test.tsx` passing. Paste the full
terminal output, not a summary. (`DashboardView.test.tsx`/`App.test.tsx`
are expected to still run as part of the same `vitest` invocation since
they live in the same directory — if either fails, that failure must be
shown too, but fixing it is explicitly out of this slice's scope per
below; a failing-but-out-of-scope file must be clearly called out as such
in the done-check output, not silently ignored.)

Out-of-scope:
- Making `DashboardView.test.tsx` or `App.test.tsx` pass — both have
  known jsdom-fragility risk (drag events, canvas rendering, real
  `<StrictMode>` double-invoke timing) flagged in their own comments,
  and forcing them into this slice risks turning a day-sized dependency-
  wiring slice into an open-ended debugging one. A follow-on slice, once
  this one's proven the runner itself works, is the right size for that.
- `@testing-library` or any other test-utility library beyond vitest +
  jsdom.
- CI / GitHub Actions wiring for the new test script — separate slice.
- ESLint/ruff/mypy tooling — already a separate, unaddressed open
  question, not this slice's job.
- Any new test file or new test case beyond what already exists in
  `SqlDetails.test.tsx`/`FollowUpChips.test.tsx`.
