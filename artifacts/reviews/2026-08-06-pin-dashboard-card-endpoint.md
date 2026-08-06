# Review gate — pin-dashboard-card-endpoint

Date: 2026-08-06
Brief: plans/briefs/2026-08-06-pin-dashboard-card-endpoint.md
Diff reviewed: working tree diff on `main` (app/main.py +59/-1, new
tests/test_api_dashboard_cards.py, new
plans/briefs/2026-08-06-pin-dashboard-card-endpoint.md)

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review
`git diff --stat -- app tests`: `app/main.py | 60 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-` (1 file changed, 59 insertions, 1 deletion), plus one new ~305-line test file. Fully read line by line. PASS.

## 2. The stated goal matches the actual change
Brief's Goal: add `POST /api/dashboards/{id}/cards` — creates one
`DashboardCard` row under an existing dashboard and returns it; 404s
immediately with zero DB writes if the dashboard id doesn't exist.

Diff adds exactly: the `Dashboard`/`DashboardCard` import,
`CreateDashboardCardRequest`/`DashboardCardDetail` Pydantic models, and
the `create_dashboard_card` route implementing that exact behavior.
Nothing else in `app/main.py` touched — no scope creep, no missing
behavior. PASS.

## 3. The eval or test passed
No LLM behavior changed by this slice, so no eval run required. Done-check
run fresh:
```
$ .venv/Scripts/python -m unittest discover -s tests -p "test_api_dashboard_cards.py" -v
test_overview_dashboard_survives_this_tests_cleanup ... ok
test_response_chart_spec_json_matches_the_nested_dict_posted ... ok
test_response_dashboard_id_matches_the_url ... ok
test_response_echoes_the_posted_title_question_and_sql ... ok
test_response_has_a_created_at_timestamp ... ok
test_response_has_exactly_the_briefs_eight_fields ... ok
test_response_id_is_an_int ... ok
test_response_position_matches_the_posted_value ... ok
test_returns_200 ... ok
test_row_really_exists_in_a_fresh_session_with_the_posted_values ... ok
test_persists_no_dashboard_card_rows_for_that_dashboard_id ... ok
test_returns_404 ... ok

Ran 12 tests in 1.351s

OK
```
Sibling suite (`test_app_db.py`, 13 tests) also re-run clean, confirming no regression to the ORM layer this slice reused. PASS.

## 4. The no-slop review found no unresolved issues
`no-slop-reviewer` subagent dispatched twice (pre-implementation pre-gate,
then final confirmation on the finished diff). No blocking findings
either time. Two low-severity stylistic notes surfaced, both resolved by
explicit accepted-as-is judgment (not code changes):

- `DashboardCardDetail` is constructed right after `session.flush()`,
  before `session.commit()` — unlike `create_conversation`'s literal
  after-commit construction. Resolution: accepted as-is. Harmless because
  `async_session_factory` sets `expire_on_commit=False`
  (`app/db/session.py:39`) and Postgres' implicit `RETURNING` on INSERT
  populates `card.id`/`card.created_at` at flush time — proven correct by
  `test_response_has_a_created_at_timestamp` and the fresh-session
  row-existence test actually passing against the real dev Postgres, not
  just asserted.
- The 404 is raised from inside the `async with session:` block rather
  than after it closes, unlike `post_conversation_message`'s literal
  style. Resolution: accepted as-is. `AsyncSession.__aexit__` still
  closes/rolls back cleanly on the exception, and
  `test_persists_no_dashboard_card_rows_for_that_dashboard_id` proves zero
  rows are written.

All other no-slop categories (dead code, unhandled errors, duplication,
naming, untested edges, comments, consistency, scope, fake-done, verified
vs. claimed) passed clean both times. PASS.

## 5. The shipping proof is attached
Real `uvicorn` dev server started on port 8010 (not just the in-process
`TestClient` the tests use) and hit with real `curl` requests:
```
=== Happy path: POST a real card to the real running server ===
HTTP/1.1 200 OK
{"id":56,"dashboard_id":1,"title":"Gate shipping-proof card","question_text":"how many orders shipped late?","sql_text":"select 1","chart_spec_json":{"type":"bar"},"position":0,"created_at":"2026-08-06T07:08:17.990623Z"}

=== Unknown dashboard id: expect 404, zero writes ===
HTTP/1.1 404 Not Found
{"detail":"dashboard not found"}
```
Proof card (id 56) deleted afterward via `_delete_dashboard_card()`;
seeded Overview dashboard (id 1) confirmed still present
(`_get_overview_dashboard_ids()` → `[1]`). Server stopped. PASS.

## Rejected or changed
Nothing rejected outright. The two no-slop stylistic notes above (check
4) were accepted as-is rather than changed — forcing literal
before/after-commit or inside/outside-block mirroring of the cited
patterns would add no correctness value, and both are proven functionally
equivalent by the passing real-DB test suite.

## Verdict
accept — all five checks green.
