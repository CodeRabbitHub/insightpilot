# Review gate — react-vite-scaffold

Date: 2026-08-05
Brief: plans/briefs/2026-08-05-react-vite-scaffold.md
Diff reviewed: working tree — app/main.py (modified), new `web/` directory
(Vite+React+TS+Tailwind scaffold), plans/briefs/2026-08-05-react-vite-scaffold.md
(new), artifacts/design/2026-08-05-react-vite-scaffold.md (new), plus an
out-of-brief infrastructure fix: .claude/settings.json and
.claude/hooks/capture_commit.py (see Check 2 and Rejected/changed below).

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review
`git diff --stat -- app/main.py .claude/settings.json .claude/hooks/capture_commit.py`:
```
.claude/hooks/capture_commit.py | 11 ++++++++++-
.claude/settings.json           |  6 +++---
app/main.py                     |  8 ++++++++
3 files changed, 21 insertions(+), 4 deletions(-)
```
Plus the new `web/` directory: 14 hand-authored/generated-once files, 350
lines total (`README.md` 11, `index.html` 13, `package.json` 26,
`postcss.config.js` 6, `tailwind.config.js` 9, `tsconfig.app.json` 27,
`tsconfig.json` 7, `tsconfig.node.json` 24, `vite.config.ts` 7,
`src/App.tsx` 146, `src/api.ts` 37, `src/index.css` 3, `src/main.tsx` 10,
`.gitignore` 24) plus `package-lock.json` (npm-managed, not read
line-by-line, standard for any Node project) and `public/favicon.svg`
(Vite-template default icon, unchanged). `web/dist/` (build output) is
untracked, correctly excluded by `web/.gitignore`. Every hand-authored
line was read. **PASS.**

## 2. The stated goal matches the actual change
Brief's Goal: stand up React 18 + Vite + TypeScript + Tailwind in `web/`
with one page — list conversations via `GET /api/conversations`, click
through to detail via `GET /api/conversations/{id}` — plus CORS on the
backend for the Vite dev origin. The diff does exactly this: `src/App.tsx`
implements the list/detail toggle per the approved design note (single
`selectedId` state, no router, no split-pane); `src/api.ts` mirrors the
three backend Pydantic models field-for-field; `app/main.py` gains
`CORSMiddleware` scoped to `http://localhost:5173` only, every existing
route otherwise byte-for-byte unchanged (confirmed via diff — additions
only). No message composing, no `POST` calls, no SSE, no ECharts, no
shadcn/ui, no router, no docker-compose wiring — all correctly absent per
Out-of-scope.

One out-of-brief item: **`.claude/settings.json` and
`.claude/hooks/capture_commit.py`** were changed mid-session. Cause:
running `npm install` inside `web/` shifted the session's shared shell
cwd, which broke the PreToolUse/PostToolUse hooks (they invoked
`python .claude/hooks/*.py` via a relative path) for every subsequent
Bash/PowerShell call — a real, blocking failure, not a proactive
improvement. Fix: hook commands now resolve the repo root via
`$(git rev-parse --show-toplevel)` instead of assuming cwd. This is
flagged explicitly here, per category 8 of the no-slop checklist, rather
than smuggled into the diff. **PASS**, with that one flagged addition
named.

## 3. The eval or test passed
No LLM-behavior/prompt changes in this slice, so no eval run required.
Done-check run fresh, after the no-slop fixes below (including turning on
`strict: true` in both tsconfigs):
```
$ cd web && npm run build

> web@0.0.0 build
> tsc -b && vite build

vite v8.2.0 building client environment for production...
transforming...✓ 16 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.46 kB │ gzip:  0.29 kB
dist/assets/index-D7EbC3tu.css    5.34 kB │ gzip:  1.85 kB
dist/assets/index-DvBiDm5a.js   143.11 kB │ gzip: 46.59 kB

✓ built in 1.11s
```
Exits 0. **PASS.**

## 4. The no-slop review found no unresolved issues
`no-slop-reviewer` subagent dispatched against the full diff (including
the settings.json/capture_commit.py fix, explicitly flagged for scope
review). Six findings, all fixed, none rejected:

1. **[Scope]** `npm create vite` pulled React 19 and Tailwind v4 by
   default — a real deviation from ARCHITECT.md's pinned "React 18 +
   ... Tailwind" decision, caught before this gate (not a formal
   no-slop-reviewer finding, but the same category): pinned
   `react`/`react-dom`/`@types/react`/`@types/react-dom` to 18.x, and
   `tailwindcss` to `^3` (matching the postcss+autoprefixer setup the
   brief's Constraints pre-approved by name; Tailwind v4 uses a different,
   non-pre-approved plugin mechanism).
2. **[Scope]** `.claude/settings.json` initially hardcoded a
   machine-specific absolute path (`C:/Users/AmanRoland/...`) — portable
   only for this one clone. Fixed: switched to
   `$(git rev-parse --show-toplevel)`, verified working from a
   subdirectory.
3. **[Unhandled errors]** `capture_commit.py`'s new `git rev-parse` call
   had no `try/except`, unlike its neighboring `git log` call — a bare
   `FileNotFoundError` would crash the hook for every later tool call,
   reintroducing the exact failure being fixed. Fixed: wrapped in
   `try/except`, falls back to a silent no-op like the existing pattern.
4. **[Scope/Dead code]** `oxlint` (dependency, config, and `lint` script)
   came bundled from the Vite template by default — not on the brief's
   dependency allow-list and never invoked by the done-check. Fixed:
   uninstalled, `.oxlintrc.json` deleted, `lint` script removed.
5. **[Untested edges — concurrency]** `App.tsx`'s detail-fetch effect had
   no staleness guard — clicking conversation A then B before A's fetch
   resolves could overwrite the view with A's late response. Fixed: added
   a `stale` flag set in the effect's cleanup, checked before every state
   update.
6. **[Fake done]** Neither `tsconfig.app.json` nor `tsconfig.node.json`
   set `strict: true` (a gap in the current `npm create vite` template
   default) — the done-check's "type-checks cleanly" framing implied more
   safety than was actually enforced; `catch (e: Error)` in `App.tsx` was
   an unchecked, unsound assertion strict mode wouldn't have caught
   anyway. Fixed: `strict: true` added to both tsconfigs; the `.catch`
   callbacks now type their parameter `unknown` and narrow with
   `instanceof Error` via a small `errorMessage()` helper.

Also fixed as a minor, uncategorized cleanup: `web/README.md`'s stock
Vite-template boilerplate (referenced the now-removed oxlint) rewritten to
describe this project's actual dev commands.

Build re-run fresh after all fixes (Check 3 above) — still exits 0, now
under `strict: true`. No unresolved findings remain. **PASS.**

## 5. The shipping proof is attached
Real backend + real Vite dev server + a real headless Chrome driven over
the DevTools Protocol (chromium-cli and Playwright both unavailable in
this environment; drove Chrome's own CDP directly instead — no new
dependency installed for this, `chrome.exe` was already present on the
machine):

```
$ curl -s http://localhost:8000/api/conversations | python -c "..."
22   # real, pre-existing conversations from prior slices' shipping proofs

$ node drive.mjs ws://localhost:9222/... list.png detail.png
CLICK_RESULT: CLICKED: Untitled | #155 · 8/5/2026, 11:46:21 AM
CONSOLE_ERRORS: []
```
List-view screenshot: real conversation rows, newest-first, `#id ·
created_at` format, matching the design note.
Detail-view screenshot (after the driver's real click on the first row):
conversation #155's actual `USER`/`ASSISTANT` messages rendered as
`<pre>`-formatted JSON — a real question ("What are the top 5 product
categories by number of orders?") and its real generated SQL + result
rows — plus a working "← Back" control. Zero browser console errors.

Throwaway processes (uvicorn on 8000, Vite dev server on 5173, headless
Chrome with its debug port on 9222) all stopped afterward; confirmed via
`netstat` that all three ports are free. **PASS.**

## Rejected or changed
- React 19 / Tailwind v4 (the `npm create vite` defaults) rejected in
  favor of React 18 / Tailwind v3, to match ARCHITECT.md's pinned
  decision and the brief's pre-approved postcss+autoprefixer setup.
- `oxlint` (template default) rejected — not on the brief's dependency
  allow-list, unused by the done-check.
- The hardcoded absolute path in the emergency hook fix rejected in favor
  of a portable `git rev-parse --show-toplevel` resolution.
- `capture_commit.py`'s unguarded `git rev-parse` call rejected in favor
  of a try/except matching its neighbor's existing failure-handling
  pattern.
- The stale-response race in the detail-fetch effect rejected in favor of
  adding a cleanup-scoped staleness guard.
- Non-`strict` TypeScript config rejected in favor of `strict: true` plus
  a sound `unknown`-typed catch helper.
- Nothing from the brief's Outputs was dropped or substituted.

## Verdict
**accept** — all five checks green.
