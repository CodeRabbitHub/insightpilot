# Review gate — patch-dashboard-card-endpoint

Date: 2026-08-06
Brief: plans/briefs/2026-08-06-patch-dashboard-card-endpoint.md
Diff reviewed: working tree diff of `app/main.py` +
`tests/test_api_dashboard_cards.py` (uncommitted, about to be committed
by this gate's acceptance)

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review

```
 app/main.py                       |  38 +++
 tests/test_api_dashboard_cards.py | 601 +++++++++++++++++++++++++++++++++++++-
 2 files changed, 638 insertions(+), 1 deletion(-)
```
38 lines of real implementation (one Pydantic model, one route). The
601-line test file diff is almost entirely repetitive test-class
boilerplate (setUp/tearDown/assertions) matching this file's own
established per-class pattern — read line by line during implementation
and again during the no-slop passes below. `plans/logs/_auto-capture.md`
also shows changed in `git status` but is a pre-existing, unrelated
capture-hook artifact — not part of this slice, excluded from this
review.

## 2. The stated goal matches the actual change

Brief's Goal: add `PATCH /api/cards/{id}` that partially updates a
`DashboardCard`'s `title` and/or `position` — whichever the body
supplies, leaving omitted fields unchanged — returning the updated card;
404 if the id doesn't exist.

Diff: adds exactly `PatchDashboardCardRequest` (`title: str | None`,
`position: int | None`, both defaulting to `None`) and
`patch_dashboard_card` (`PATCH /api/cards/{card_id}`), which does
`session.get` → 404-if-None → apply each field only if `is not None` →
flush → build `DashboardCardDetail` → commit. No new pool, no new
dependency, no touch to `sql_text`/`question_text`/`chart_spec_json`/
`dashboard_id`, and `POST /api/dashboards/{id}/cards` /
`GET /api/dashboards/{id}` are untouched. Matches the Goal and every
Constraint exactly; no extra "improvements," nothing missing.

## 3. The eval or test passed

Done-check run fresh by the reviewer (this session), after both no-slop
fixes were applied:

```
.venv/Scripts/python -m unittest discover -s tests -p "test_api_dashboard_cards.py" -v
...
Ran 54 tests in 8.738s

OK
```

No LLM behavior changed in this slice, so no eval run is required.

## 4. The no-slop review found no unresolved issues

Two passes of the `no-slop-reviewer` subagent were run.

**Pass 1 finding** — category 5 (untested edges): no test PATCHed a
falsy-but-meaningful new value (`position: 0` / `title: ""`) to prove
the route's `is not None` check (vs. a truthiness check) is what's
actually running. **Resolved**: added
`PatchDashboardCardFalsyNewValuesTests`, which seeds a card with
non-falsy values and PATCHes `{"title": "", "position": 0}`, asserting
both apply via the response and a fresh DB session.

**Pass 2 finding** (re-review after the pass-1 fix, on the updated diff)
— category 5 again: no test PATCHed a body also containing disallowed
fields (`sql_text`, `dashboard_id`, `chart_spec_json`, `question_text`)
to prove the brief's "those stay exactly as pinned" Constraint holds at
the HTTP layer, not just structurally (Pydantic silently drops unknown
keys; there's no `extra="forbid"`). **Resolved**: added
`PatchDashboardCardIgnoresDisallowedFieldsTests`, which PATCHes a body
containing all four disallowed fields alongside a legitimate `title`
change and asserts all four stay at their seeded values, via both the
response and a fresh session.

Pass 2 confirmed no further findings across all 10 checklist categories
(dead code, unhandled errors, duplication, naming, untested edges,
comments, consistency, scope, fake done, verified-not-claimed). No
unresolved findings remain.

## 5. The shipping proof is attached

Real `uvicorn` dev server (not `TestClient`), real `curl`, real dev
Postgres:

```
=== POST a real card onto Overview (dashboard 1) ===
{"id":851,"dashboard_id":1,"title":"Proof card before PATCH",...,"position":42,...}

=== PATCH title only ===
{"id":851,...,"title":"Renamed by real PATCH",...,"position":42,...}

=== PATCH position only ===
{"id":851,...,"title":"Renamed by real PATCH",...,"position":0,...}

=== PATCH both ===
{"id":851,...,"title":"Both changed",...,"position":99,...}

=== PATCH empty body (no-op) ===
{"id":851,...,"title":"Both changed",...,"position":99,...}   <- unchanged from prior response

=== PATCH unknown id ===
{"detail":"card not found"}
HTTP 404
```

Proof card 851 deleted afterward via `_delete_dashboard_card`; confirmed
absent from a subsequent `GET /api/dashboards/1`. Dev server process
stopped afterward (confirmed via a follow-up request returning
connection-refused).

## Rejected or changed

- Two no-slop findings (falsy-new-values coverage, disallowed-fields
  coverage) were not rejected but fixed in place by adding the two test
  classes described above, before this gate closed. Nothing from the
  brief or plan was rejected — the implementation matched the approved
  plan as written.

## Verdict

**accept** — all five checks green.
