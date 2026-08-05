# Slice log — react-vite-scaffold

Date: 2026-08-05
Brief: plans/briefs/2026-08-05-react-vite-scaffold.md

## The plan you approved
Stand up `web/` as a React 18 + Vite + TypeScript + Tailwind scaffold
with one component: `selectedId` state toggles between a list view
(`GET /api/conversations`) and a detail view (`GET
/api/conversations/{id}`), each message rendered as a role badge +
`<pre>`-formatted JSON — no split-pane, no router, no charts. Add
`CORSMiddleware` to `app/main.py` scoped to the Vite dev origin. Design
note: artifacts/design/2026-08-05-react-vite-scaffold.md.

## The diff you accepted
Commit `21add48` — "Add React/Vite/Tailwind scaffold with conversations
list/detail page". 22 files changed, 2735 insertions(+), 4 deletions(-).
Full stat in `plans/logs/_auto-capture.md`. Gate record (all five checks
green, verdict accept): artifacts/reviews/2026-08-05-react-vite-scaffold.md.

## The done-check output
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
Shipping proof (real backend + real Vite dev server + headless Chrome
driven over the DevTools Protocol, since chromium-cli/Playwright weren't
available in this environment): list view rendered 22 real conversations;
a real click loaded conversation #155's actual question and generated SQL
in the detail view; zero browser console errors. Full transcript in the
gate record.

## One thing you rejected or changed
`npm create vite@latest web -- --template react-ts` defaulted to **React
19.2.8 and Tailwind v4.3.3** — silently off ARCHITECT.md's pinned "React
18 + Vite + TypeScript frontend" decision, and off the brief's own
pre-approved postcss+autoprefixer Tailwind setup (Tailwind v4 uses a
different, non-pre-approved plugin mechanism). Caught before the no-slop
pass, by checking `web/package.json` right after scaffolding instead of
trusting the generator's defaults. Fixed: pinned `react`/`react-dom` and
their `@types/*` packages to `^18`, pinned `tailwindcss` to `^3` (keeping
the already-installed `postcss`/`autoprefixer`), re-ran `npx tailwindcss
init -p` against the v3 CLI.

This is the first frontend slice in the project, so this is a first
occurrence, not a repeat — no promotion to CLAUDE.md/no-slop.md yet, per
the ratchet's second-repetition rule. Worth watching: any future slice
that runs a project scaffolding generator (`npm create`, `cookiecutter`,
etc.) should check the generated manifest against ARCHITECT.md's pinned
versions before building on top of it, since generators default to their
own latest, not this repo's decisions.

(The no-slop pass itself also caught and fixed five more issues — an
unapproved `oxlint` dependency the template bundled, a hardcoded
machine-specific path in an emergency hook fix, an unguarded subprocess
call, a stale-response race in the detail view, and missing `strict: true`
in both tsconfigs — all detailed in the gate record's Check 4.)

## The next smallest slice
Wire up message composing into the existing page: a text input that
`POST`s a new question to `/api/conversations/{id}/messages` and consumes
its SSE response, appending the streamed result to the message list —
still plain-rendered (no ECharts, no shadcn/ui yet), proving the
write/streaming path in the browser for the first time.
