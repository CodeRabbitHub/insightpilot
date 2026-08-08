# Brief — app-strictmode-fetch-guard

Date: 2026-08-08
Milestone: M6 Dashboard (robustness carried over from the M5/M6 chat+dashboard UI — same bug class as the just-shipped `DashboardView.tsx` fix)

Goal:
Fix `App.tsx`'s conversations-list mount effect so React 18 StrictMode's
dev-only double-invoke can never let a stale duplicate `fetchConversations`
response overwrite newer state — the same bug class just fixed in
`DashboardView.tsx`, in a different file.

Constraints:
- Stack: React 18 + TypeScript, no new dependency (per CLAUDE.md's
  no-new-dependency rule) — the fix stays inside `web/src/App.tsx`.
- Touch only `App.tsx`'s conversations-list `useEffect` (currently lines
  ~164-171) — no backend change, no change to any other part of `App.tsx`
  (the conversation-detail effect at lines 173-194 already has the correct
  guard and must not be touched; `ConversationList`,
  `ConversationDetailView`, message-sending, and view switching are
  unrelated to this race and stay untouched).
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
- `web/src/components/DashboardView.tsx`'s now-fixed mount effect (prior
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
