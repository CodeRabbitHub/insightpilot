---
name: handoff
description: Rewrite HANDOFF.md at the end of a slice. Use after /capture, as the last act of the session.
---

Close the loop: write what the next session will read first.

1. Read templates/handoff.md. Rewrite HANDOFF.md completely — it describes
   NOW, not history (history lives in plans/logs/).
2. "State of the work" may contain only facts a done-check demonstrated
   this session. No "should work". If it wasn't verified, list it under
   open questions instead.
3. Paste the latest proof output.
4. Write the FULL brief for the next slice (all six templates/brief.md
   fields), using the "next smallest slice" line from the log as the seed.
   Apply the same pushback rules as /brief: single-outcome goal, binary and
   runnable done-check, non-empty out-of-scope.
5. Confirm with the user, save, then tell them: /clear — the next slice
   starts in a fresh session that reads this file.
