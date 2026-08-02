# Review gate — <slice name>

Date:
Brief: <link>
Diff reviewed: <commit hash or branch diff>

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review
<!-- git diff --stat. If you can't honestly read every line, the check
     FAILS — split the diff and gate the pieces. -->

## 2. The stated goal matches the actual change
<!-- The brief's Goal vs what the diff actually does. Extra "improvements"
     or missing behavior both fail this check. -->

## 3. The eval or test passed
<!-- The done-check (and eval, if LLM behavior), RUN FRESH BY THE REVIEWER,
     output pasted verbatim below. -->
```
<paste>
```

## 4. The no-slop review found no unresolved issues
<!-- Reviewer subagent findings + how each was resolved. An open finding
     with no resolution fails this check. -->

## 5. The shipping proof is attached
<!-- Evidence it works in reality, not just in tests: the command output,
     screenshot, rendered page, or API response from actually running it. -->

## Rejected or changed
<!-- At least one thing, or explicit justification for zero. -->

## Verdict
<!-- accept / accept-with-changes / reject — with all five checks green. -->
