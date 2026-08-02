---
name: brief
description: Start a new slice by writing its brief. Use when beginning new work, or when HANDOFF.md has no brief for the next slice.
---

Write the contract for the next slice of work.

1. Read templates/brief.md for the required fields. Read HANDOFF.md and
   PLAN.md to know where the project is and which milestone is next.
2. Interview the user field by field. Draft proposals from context; don't
   make them type everything.
3. Push back — do not save the brief — while any of these hold:
   - The done-check is not binary (contains "well", "properly", "good") or
     is not runnable as a single command.
   - The goal is more than one outcome. Split it.
   - The slice looks bigger than ~a day of work. Propose a smaller cut.
   - Out-of-scope is empty. There is always a non-goal.
   - Constraints are silent on the stack (invites dependency drift —
     check ARCHITECT.md and echo the relevant decisions).
4. Save to plans/briefs/YYYY-MM-DD-<slug>.md.
5. Read the finished brief back to the user and get an explicit yes before
   any planning or code. The brief is Gate 0.
