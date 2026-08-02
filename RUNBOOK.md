# Project Runbook — How I Build With AI Agents

This is my operating system for software projects, built around a simple
observation: **AI makes writing code cheap, so the engineering value moves to
three places — defining work precisely, filtering output ruthlessly, and
compounding what I learn.** Everything in this document serves one of those
three.

The method is tool-agnostic; my current stack is Claude Code, whose skills,
subagents, and hooks turn the method into working machinery (§7). The whole
thing lives as a starter kit I copy for every new project.

---

## 1. The principles

1. **Contracts before code.** No work starts without a written brief: the
   goal, the constraints, and a runnable done-check. "Done" is never a
   feeling — it's a command whose output I can paste.
2. **Evidence over claims.** "It works" is an assertion; test output is a
   fact. Anything reported as working was actually run, in this session,
   with proof attached.
3. **Small slices.** Work is cut into pieces of a few hours to a day, each
   independently valuable and independently provable. Small slices ship,
   teach fast, and fail cheaply.
4. **Two human gates per slice.** I approve the plan before code exists
   (cheap to redirect) and run a five-check review before anything merges
   (last filter). Between the gates, agents run autonomously — the gates are
   what make that autonomy safe.
5. **The second-repetition rule.** Anything I do, say, or correct twice gets
   automated: a standing rule, a hook, a skill, a subagent, or an eval case.
   The system improves as a side effect of using it.

---

## 2. The loop at a glance

```
ONCE PER PROJECT   plan → architecture (irreversible only) → agent context
                   → copy the kit → connect tools → git init

PER SLICE          read handoff → six-line brief → plan ⟨GATE 1: approve⟩
                   → subagent writes tests from the brief → build
                   ⟲ (stop-hook test loop, max 3 attempts)
                   → no-slop subagent (10-category rubric)
                   → ⟨GATE 2: the five-check gate⟩ → merge → capture log
                   (+ eval case if AI behavior) → rewrite handoff → clear

ALWAYS RUNNING     2nd repetition → automate it
                   3 failures → stop and re-plan, never thrash
                   nothing merges unreviewed · nothing done without proof

PER PROJECT END    lessons → kit → next project starts stronger
```

The rest of this document unpacks each line.

---

## 3. The file layout

Every project has the same skeleton, so anyone — agent or human — can orient
in a minute:

```
project/
├── CLAUDE.md           Agent context: commands, standing rules, map. Thin.
│                       Loaded automatically into every agent session.
├── PLAN.md             Problem, users, ordered milestones. One page.
├── ARCHITECT.md        Irreversible decisions only, each with a 1-line why.
├── HANDOFF.md          Live state: verified facts + the next brief.
│                       Rewritten at the end of every slice.
├── RUNBOOK.md          This document.        WORKFLOW.md   The cheat sheet.
├── plans/briefs/       One six-line contract per slice (before work).
├── plans/logs/         One evidence record per slice (after work).
├── artifacts/reviews/  Five-check gate records.
├── artifacts/design/   Approved mockups — the visual contracts.
├── evals/  tests/      Quality checks: probabilistic and deterministic.
├── templates/          The blank forms (§5-6). Single source of truth —
│                       skills and reviewer agents READ these, never copy
│                       them, so editing a template upgrades the machinery.
└── .claude/
    ├── skills/         /brief  /gate  /capture  /handoff
    ├── agents/         test-writer · no-slop-reviewer
    ├── hooks/          danger_block · stop_verify · capture_commit
    └── settings.json   Wires hooks to the agent lifecycle
```

Two files matter most, and they must never merge: **CLAUDE.md is stable
rules** (changes rarely, loads every session); **HANDOFF.md is volatile
state** (changes every slice). Mixing them bloats every session with stale
state.

---

## 4. Phase 0 — starting a project (~30 min, once)

1. **PLAN.md** — the problem, who it's for, milestones in order. Milestones
   are for *ordering*, not detail; each gets decomposed into briefs only
   when its turn comes.
2. **ARCHITECT.md** — only decisions that are expensive to reverse:
   language, storage, component boundaries, external services. Everything
   else stays deliberately undecided; architecture that outruns the code is
   fiction. Changes later happen by explicit amendment at a gate, never by
   drift.
3. **CLAUDE.md** — fill in what the project is and its run/test commands.
4. **Copy the kit** from the last project — templates, skills, agents,
   hooks. This step is where compounding pays out.
5. **Connect tools** (MCP): whatever agents must reach — GitHub, a browser,
   tickets, a database.
6. `git init`, commit the docs, write the first brief into HANDOFF.md.

---

## 5. The slice loop in detail

Each slice runs in a **fresh agent session** on **its own branch**. The loop
is closed: the last step writes the file the first step reads.

### Step 1 — READ
The session opens by reading HANDOFF.md: verified state, open questions, and
the brief for this slice (written by the previous session while its context
was hot). This is why a fresh session starts smart, not cold.

### Step 2 — BRIEF (`/brief`)
The contract, exactly six lines:

```
Goal:         the one outcome, in a sentence.
Constraints:  what it must (and must not) do. Stack, perf, style, security.
Inputs:       what the agent starts with. Files, data, an API, an example.
Outputs:      what exists when it's finished. Files, endpoints, behavior.
Done-check:   the concrete test that proves it works.
Out-of-scope: what NOT to touch, so it doesn't wander.
```

The `/brief` skill interviews me into these fields and **refuses to save**
while any of these hold: the goal is more than one outcome; the done-check
isn't binary or isn't runnable as a single command; the slice looks bigger
than a day; out-of-scope is empty; constraints are silent on the stack.
A brief that's hard to fill in means the slice is too big or the plan above
it is too vague — fix that first.

### Step 3 — PLAN (Gate 1)
The agent proposes an approach in plan mode — no code yet. If the slice has
a user-facing surface, a **design note** is written now: who uses it, the
decision, the one rejected alternative, why. External design tools (Stitch,
Figma, v0) plug in here — their chosen export goes to `artifacts/design/`
and becomes the visual contract Gate 2 checks against. Their generated code,
if imported at all, enters as an untrusted draft that faces the same review
as any other diff; their framework assumptions are *proposals* to amend
ARCHITECT.md, never silent decisions.

**⟨GATE 1 — I approve the plan and design.⟩** Redirecting here costs one
sentence; redirecting a finished diff costs a rework cycle.

### Step 4 — TESTS (test-writer subagent)
A dedicated subagent writes failing tests **from the brief alone** — it is
instructed not to read the implementation plan, so the tests derive expected
behavior from the done-check and mine the Constraints for edge cases (perf
limits, security rules, and forbidden behaviors are all testable).
Independence from the implementation is the entire point: tests written by
the builder's context inherit the builder's blind spots.

### Step 5 — BUILD (the automated loop)
The agent implements until the tests pass. Enforcement is mechanical: a
**Stop hook** runs the suite every time the agent claims to be done —
failures bounce it back with the output and the instruction *"fix the code,
never the test."* The loop is **capped at 3 attempts** (§8, the breaker).

### Step 6 — PRE-GATE (no-slop-reviewer subagent)
A read-only reviewer walks the ten-category no-slop checklist (§6) against
every changed file and reports findings ranked by severity, with file:line
evidence. It has no edit tools — a reviewer that physically cannot change
code is structurally trustworthy. Mechanical findings get fixed before a
human ever looks; judgment findings surface to me unfiltered.

### Step 7 — GATE 2 (`/gate`): the five-check gate
Before any change goes out, the gate is written down. Five checks, walked in
order — each is a cheap filter for the next, and **all five pass or nothing
merges**:

```
1. The diff is small enough to review.
     If I can't honestly read every line, the check fails —
     split the diff and gate the pieces. (Repeated failures here
     mean the BRIEFS are too big — feedback to step 2.)
2. The stated goal matches the actual change.
     The brief's Goal vs what the diff does. Missing behavior fails;
     unrequested "improvements" fail too.
3. The eval or test passed.
     Run fresh BY ME (not trusted from the builder), output pasted.
4. The no-slop review found no unresolved issues.
     Every finding fixed, or carrying a written one-line exception.
5. The shipping proof is attached.
     Evidence from REALITY, not just tests: the running command, the
     rendered page, the API response. A test suite can be green while
     the app crashes on startup — this check closes that gap.
```

The record (artifacts/reviews/) also names **at least one thing I rejected
or changed** — if I can't name one, I was rubber-stamping, and the record
says so honestly.

### Step 8 — COMMIT
Only now. The merge is the acceptance record.

### Step 9 — CAPTURE (`/capture`)
The slice log: a hook has already appended the commit hash and stat
automatically; I add the judgment — the plan I approved, the thing I
rejected, the next smallest slice. If the slice touched AI behavior
(prompt, model, retrieval), the quality issue or success becomes a **new
eval case** — evals accumulate for the life of the project and re-run on
every prompt or model change, because prompt changes break things
*elsewhere*.

### Step 10 — HANDOFF (`/handoff`) and CLEAR
HANDOFF.md is rewritten completely: verified facts only (anything not
demonstrated by a done-check this session is an open question, not a
state), the proof output, and **the full six-line brief for the next
slice — written now, while context is hot.** Then the session ends. The
next slice starts fresh, reading this file. That one habit is deliberate
context hygiene: no slice runs in a previous slice's polluted context.

---

## 6. The No-Slop Checklist (the quality rubric)

Walked top to bottom against every file created or changed. Each item:
**fix it, or write one line on why it's a deliberate exception** — a claimed
exception that isn't written down is itself a finding. Full checklist in
`templates/no-slop.md`; the ten categories:

1. **Dead code** — no unused variables/imports/functions, no commented-out
   blocks (that's what git is for), no unreachable branches, nothing added
   "just in case." *Dead code is a lie about what the program does.*
2. **Unhandled errors** — every fallible call (I/O, network, parse,
   external command) has a real failure path; no swallowed exceptions; no
   errors logged then ignored; failure messages say what failed *and what
   to do*.
3. **Duplication** — third occurrence means extract; no parallel structures
   kept in sync by hand; shared logic lives in one place.
4. **Naming** — no `data`/`temp`/`obj`/`manager` without a qualifier; names
   say what the thing is, specifically; booleans read as questions
   (`isReady`); one vocabulary per concept (never `user` here, `account`
   there).
5. **Untested edges** — empty, null, zero, negative, max-size; the unhappy
   path when a dependency is down; concurrency if anything runs in
   parallel; and the deepest one: *the eval actually covers what "done"
   means, not just the happy path* — this reviews the tests themselves.
6. **Comments** — never restate the code; the ones that remain explain
   *why* (the non-obvious decision, the constraint, the gotcha); no stale
   comments describing code that changed.
7. **Consistency with the codebase** — match the surrounding idioms and
   utilities, not the agent's (or my) personal defaults; same
   error-handling, logging, and import style as the neighbors.
8. **Scope** — everything in the brief; anything extra flagged explicitly,
   not smuggled in; nothing from the brief silently dropped.
9. **Fake done** — no untracked TODO/FIXME; no stubbed returns or
   hardcoded values pretending to be implementation; no
   works-on-my-machine assumptions; no debug prints left in.
10. **Verified, not claimed** — anything reported "working" was actually
    run; anything reported "done/deployed/live" has *same-session* proof (a
    passing test, a curl, a screenshot, a log line); test failures reported
    as failures, with output — never hidden or hand-waved.

Categories 7–8 are the anti-drift pair for agent work: consistency stops an
agent imposing its defaults on the codebase; scope stops it wandering off
the brief. Category 10 is principle #2 made checkable.

---

## 7. The machinery (how the method enforces itself)

The method would decay if it lived on memory and discipline. It doesn't —
it's wired into the agent harness. Design rule throughout: **templates hold
structure, skills hold procedure, hooks hold enforcement** — and skills and
agents *reference* the templates, so there is exactly one file to edit when
a standard evolves.

**Skills** (packaged procedures, invoked as slash commands):

| Command | Wraps | Behavior worth noting |
|---|---|---|
| `/brief` | step 2 | Interviews field by field; refuses vague done-checks and empty out-of-scope |
| `/gate` | steps 6–7 | Walks the five checks in order; check 1 is an early exit for oversized diffs |
| `/capture` | step 9 | Mechanics pre-filled by hook; asks only the judgment questions; proposes promotions when a rejection repeats |
| `/handoff` | step 10 | Enforces facts-only state; won't finish without the next brief written |

**Subagents** (separate agent instances, restricted tools, own context):

| Agent | Tools | Why restricted |
|---|---|---|
| test-writer | read + write, but briefed to never read the implementation plan | Tests independent of the builder's blind spots |
| no-slop-reviewer | read-only (cannot edit) | A reviewer that can't change code can't paper over what it finds |

**Hooks** (shell scripts the harness runs automatically — rules as
machinery, not memory):

| Hook | Fires | Does |
|---|---|---|
| danger_block | before every shell command | Blocks `rm -rf`, force-push, hard reset, `.env` writes, `--no-verify` — with the reason fed back to the agent |
| stop_verify | every time the agent claims "done" | Runs the test suite; failure = agent bounced back to work with the output. Attempt 3 fires the circuit breaker: *stop fixing, summarize what the three attempts revealed, ask for a re-plan.* State resets when tests pass. |
| capture_commit | after every git commit | Appends hash + stat to an auto-capture log so `/capture` pre-fills mechanically |

**MCP / connectors** extend the agents' reach: read the ticket, create the
issues, drive a browser to screenshot the live page (which is exactly what
gate check #5 wants). Two rules keep this inside the discipline: content
*read* through connectors is **data, never instructions** (prompt-injection
defense); anything *written* to the outside world goes through a gate first.

---

## 8. Standing policies — always running, never suspended

**The ratchet: 2nd repetition → promote.** The second occurrence of
anything is a pattern; automate it before continuing. The ladder, in order
of force: repeated correction → **CLAUDE.md rule** → rule still violated →
**hook** → repeated procedure → **skill** → repeated role → **subagent** →
repeated quality failure → **eval case** → repeated "can you paste me X" →
**MCP connector**. Each promotion converts a recurring cost into a one-time
investment.

**The circuit breaker: 3 failures → re-plan.** Every retry loop is capped
at three attempts. Three genuinely different failures means the problem is
one level up — an ambiguous brief, a wrong architecture assumption, a bad
test. The agent must stop, report what each attempt revealed, and hand the
decision back to me. Attempt #7 never fixes a wrong plan; it manufactures
slop, usually by quietly weakening the test (which categories 5 and 10 of
the checklist, plus a hard rule in CLAUDE.md, forbid). The failures aren't
waste — they're diagnosis for the re-plan.

**The floor — two invariants with zero exceptions:**
- Nothing merges unreviewed.
- Nothing is "done" without pasted, same-session proof.

Their defining property: they hold *especially* under deadline pressure,
because that is exactly when skipping them is tempting and exactly when
slop gets in.

---

## 9. Parallel work — only when it's earned

Parallelism qualifies only when the workstreams are genuinely independent
(near-empty shared-files list), each has its own brief and done-check, and
I have review capacity for all of them. Otherwise it isn't two streams —
it's one stream plus a slop generator.

When it qualifies: a parallel plan (goal, workstreams, **shared files** —
the collision list; if it's long, re-cut the boundaries — review gates,
**merge order decided before work starts**, and an integration proof). One
worktree or subagent per stream, each leashed by its brief's Out-of-scope.
Streams gate separately, merge in the declared order, and the integration
proof runs after all land — individual proofs passing does not prove the
streams work together.

---

## 10. Ending a project — the compounding step

One pass through the logs and gate records, asking a single question:
*what did this project teach that the next one should start with?*
Recurring rejections → new checklist lines. New procedures → skills. New
enforcement needs → hooks. Template improvements → the kit. Then the kit —
templates, skills, agents, hooks, this runbook — carries forward.

That is the actual win condition: **the loop doesn't just ship projects.
Every project upgrades the system, and the system makes every next project
faster and cleaner than the last.**

---

## Quick reference card

```
THE CONTRACT   Goal · Constraints · Inputs · Outputs · Done-check · Out-of-scope

THE LOOP       read handoff → /brief → plan ⟨GATE 1⟩ → tests from brief
               → build ⟲ (max 3) → no-slop review → ⟨GATE 2: five checks⟩
               → merge → /capture (+ eval) → /handoff → clear

THE GATE       1 diff reviewable · 2 goal matches change · 3 test/eval passed
               4 no-slop clean · 5 shipping proof attached

THE RUBRIC     dead code · errors · duplication · naming · edges · comments
               consistency · scope · fake done · verified-not-claimed

THE GOVERNOR   2nd repetition → automate · 3 failures → re-plan
               nothing merges unreviewed · nothing done without proof
```
