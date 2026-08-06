# Slice log — pin-dashboard-card-endpoint

Date: 2026-08-06
Brief: plans/briefs/2026-08-06-pin-dashboard-card-endpoint.md

## The plan you approved

Add `POST /api/dashboards/{id}/cards` to `app/main.py`, combining two
existing patterns: `create_conversation`'s insert-flush-commit-return
shape for the happy path, and `post_conversation_message`'s
check-existence-then-404-with-zero-writes shape for an unknown dashboard
id. No new pool, no new dependency, no SQL execution/sqlglot validation
at pin time (`sql_text` stored opaquely, per the brief's Constraints).

## The diff you accepted

Commit `089c0d4` — "Add POST /api/dashboards/{id}/cards to pin a card
onto a dashboard". `app/main.py` +59/-1 (new import, two Pydantic models
`CreateDashboardCardRequest`/`DashboardCardDetail`, one route); new
`tests/test_api_dashboard_cards.py` (304 lines). Full mechanics in
`plans/logs/_auto-capture.md`'s "Commit at 2026-08-06 12:48" entry.

## The done-check output

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

----------------------------------------------------------------------
Ran 12 tests in 1.351s

OK
```
Full gate record, including the real-`uvicorn`-server shipping proof
(`curl` happy path + 404, against a real running dev server, not just
`TestClient`), is in
`artifacts/reviews/2026-08-06-pin-dashboard-card-endpoint.md`.

## One thing you rejected or changed

Nothing was changed in code, but two low-severity no-slop findings were
explicitly accepted rather than rubber-stamped past:

1. `DashboardCardDetail` is built right after `session.flush()`, before
   `session.commit()` — the brief says to mirror `create_conversation`
   "exactly," and that function builds its response *after* commit.
   Accepted as-is: `async_session_factory` has `expire_on_commit=False`
   and Postgres' implicit `RETURNING` on INSERT populates `card.id`/
   `card.created_at` at flush time, proven correct by the passing tests
   rather than just asserted.
2. The 404 is raised from inside the `async with session:` block, unlike
   `post_conversation_message`'s raise-after-the-block style. Accepted
   as-is: `AsyncSession.__aexit__` still closes/rolls back cleanly, and
   the zero-writes test proves nothing persists.

This is a first occurrence of "brief says mirror exactly, shipped code
diverges slightly but is proven equivalent" — checked prior logs in
`plans/logs/` for a repeat of this exact shape and found none, so no
promotion to CLAUDE.md/`templates/no-slop.md` this time. If this same
before/after-commit or inside/outside-block divergence gets flagged
again on a future slice, that's the trigger to promote it.

## The next smallest slice

`GET /api/dashboards/{id}` fresh-on-view: re-validate and re-execute
each pinned card's `sql_text` through sqlglot + `execute_sql()` and
return fresh rows per card, completing M6's "pin an answer, dashboard
survives restart and re-renders fresh" requirement (write side shipped
this slice, read side next).
