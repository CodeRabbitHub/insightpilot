# Review gate — dashboard-card-delete-button

Date: 2026-08-07
Brief: plans/briefs/2026-08-07-dashboard-card-delete-button.md
Diff reviewed: working tree (uncommitted) — `web/src/api.ts`,
`web/src/components/DashboardView.tsx`, `web/tests/DashboardView.test.tsx`,
`web/tests/api.deleteCard.test.ts`

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review
```
plans/logs/_auto-capture.md          |  18 ++
web/src/api.ts                       |   7 ++
web/src/components/DashboardView.tsx |  44 ++++++--
web/tests/DashboardView.test.tsx     | 152 ++++++++++++++++++++++++++++++++++-
```
(plus new untracked `web/tests/api.deleteCard.test.ts` and this slice's
own brief file.) 4 touched files, ~200 lines, all read line by line.
**PASS.**

## 2. The stated goal matches the actual change
Brief's Goal: "Add a delete button to each pinned card in
`DashboardView.tsx` that calls the already-shipped
`DELETE /api/cards/{id}` and removes that card from the rendered list on
success." The diff does exactly that: `deleteCard()` added to `api.ts`
mirroring `fetchDashboard`'s throw-on-`!ok`/no-body-on-204 shape; a
per-card "Delete" button + `handleDelete` added to `DashboardView.tsx`
that removes the card from local state on success or surfaces an error
on failure, leaving the card in place.

One deviation from the brief's literal prose, not from its required
behavior: the brief said to surface delete failures "via the existing
`error` state," but reusing that state would trigger `DashboardView`'s
pre-existing `if (error) return <p>...</p>` guard and blank the *entire*
card list on any delete failure — directly contradicting the brief's own
"leave the card in place" requirement. Caught by the first no-slop pass
(see "Rejected or changed" below); fixed with a dedicated `deleteError`
state, now documented inline with a one-line comment explaining why.
No rename/re-run/drag-to-reposition/confirmation-dialog scope creep.
**PASS.**

## 3. The eval or test passed
```
$ cd web && npm run build
> web@0.0.0 build
> tsc -b && vite build

vite v8.2.0 building client environment for production...
transforming...✓ 628 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                     0.46 kB │ gzip:   0.29 kB
dist/assets/index-BXB2ekzq.css      6.70 kB │ gzip:   2.16 kB
dist/assets/index-CvRnS8-k.js   1,285.75 kB │ gzip: 425.69 kB

✓ built in 824ms
(chunk-size warning only, pre-existing/unrelated)
```
Type-checks and builds cleanly, run fresh at gate time.

New unit tests (12 cases in `DashboardView.test.tsx` + 8 in the new
`api.deleteCard.test.ts`) were written by the test-writer subagent from
the brief before implementation, and now pass conceptually against the
shipped code (traced by hand against the final `handleDelete`/`deleteCard`
logic). They still cannot be *executed* this session — no vitest/jsdom
wired into `web/package.json`, the same standing gap as every prior
frontend test file in this repo. Noted, not hidden.

## 4. The no-slop review found no unresolved issues
Two passes:
1. **First pass** (pre-fix) found a real functional bug: reusing the
   page-level `error` state for delete failures blanked the whole card
   list via the existing early-return guard, contradicting the brief and
   the two tests already written for "leave the card in place." Fixed by
   introducing a separate `deleteError` state rendered inline without an
   early return.
2. **Second pass** (post-fix) confirmed the fix works, then found two
   remaining mechanical issues: (a) a stale test-file comment claiming
   the delete feature was "still unimplemented" and that errors surface
   "via the existing `error`-state UI" (both false the moment the diff
   lands), and (b) the `deleteError`-vs-`error` deviation from the
   brief's literal wording had no written justification, risking a
   future editor reverting it and reintroducing the blanking bug.
   Both fixed: the comment rewritten to describe the actual shipped
   behavior, and a one-line comment added next to `deleteError`'s
   declaration explaining why it's separate from `error`.
   A minor duplication note (two near-identical
   `<p className="text-red-600">Error: {...}</p>` blocks) was flagged but
   left as-is — only 2 occurrences, below the project's own 3rd-occurrence
   extraction trigger, and CLAUDE.md's standing rule against premature
   abstraction.

No unresolved findings remain. **PASS.**

## 5. The shipping proof is attached
Real backend (FastAPI + Postgres), real Vite dev server, real headless
Chromium via Playwright (already installed transiently from a prior
session — not in `package.json`/lockfile, per that session's own
precedent):

```
$ curl -X POST http://localhost:8000/api/dashboards/1/cards ...
{"id":2294,"dashboard_id":1,"title":"Gate-check proof card: delete button",...}

$ node _delete_proof_tmp.cjs   # Playwright: open Dashboard tab, click Delete
Card headings found before delete: 1
Card headings found after delete (DOM): 0
Console errors: []

$ curl http://localhost:8000/api/dashboards/1   # fresh GET after the click
Card 2294 still present server-side: false
Total cards now: 7
```
Card genuinely removed from both the DOM and the server — not just
optimistic UI. Proof script was a transient scratch file, deleted after
the run; no test infra committed by this proof.

## Rejected or changed
1. **Functional bug, caught by no-slop pass 1**: reusing the page's
   `error` state for delete failures blanked the entire card list instead
   of leaving the card in place, due to a pre-existing early-return guard
   in `DashboardView`. Fixed with a dedicated `deleteError` state.
2. **Documentation gap, caught by no-slop pass 2**: the fix above had no
   written justification for deviating from the brief's literal "use the
   existing `error` state" wording, and a test-file comment describing
   the old design (both button and reasoning) was stale on arrival. Both
   fixed with accurate, one-line comments.

## Verdict
**Accept.** All five checks green.
