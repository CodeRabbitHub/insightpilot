# Slice log — delete-dashboard-card-endpoint

Date: 2026-08-07
Brief: plans/briefs/2026-08-07-delete-dashboard-card-endpoint.md

## The plan you approved

Add a `DELETE /api/cards/{card_id}` route to `app/main.py`, mirroring
`patch_dashboard_card`'s existing existence-check-then-404 shape:
`session.get(DashboardCard, card_id)` → 404 (`{"detail": "card not
found"}`) if `None` → else `session.delete(card)` + `session.commit()`
→ `status_code=204`, no response body, no new Pydantic model. No new
pool, no new dependency. Tests written first via the test-writer
subagent, confirmed failing only on the missing route (405 Method Not
Allowed, no import errors) before implementation.

## The diff you accepted

Commit `2097aa5` — "Add DELETE /api/cards/{id} for pinned card
removal". `app/main.py` +14 lines (one route); `tests/
test_api_dashboard_cards.py` +241 lines (3 new test classes: happy
path, unknown id, sibling/parent isolation). Full stat in `plans/logs/
_auto-capture.md`'s corresponding commit entry.

## The done-check output

```
.venv/Scripts/python -m unittest discover -s tests -p "test_api_dashboard_cards.py" -v
...
----------------------------------------------------------------------
Ran 64 tests in 16.708s

OK
```
(64 = 54 pre-existing + 10 across the 3 new DELETE test classes; each
new test verifies via a fresh `async_session_factory` session, not just
the echoed response; the isolation test proves a sibling card and the
Overview dashboard row itself survive the delete.)

Shipping proof (real `uvicorn` dev server + real `curl`, not just
`TestClient`) — full transcript in `artifacts/reviews/
2026-08-07-delete-dashboard-card-endpoint.md`: posted a real card (id
1187), confirmed it present via `GET /api/dashboards/1`, `DELETE`d it
(204, empty body), confirmed via a fresh `GET /api/dashboards/1` that it
no longer appears while the dashboard's other cards remain, then
`DELETE`d an unknown id (404, exact `{"detail":"card not found"}`
body). Dev server process confirmed stopped afterward via a
connection-refused follow-up request.

## One thing you rejected or changed

Nothing rejected or changed — the no-slop-reviewer subagent returned
zero findings across all 10 checklist categories on the first pass, and
the implementation matched the brief and the established
`patch_dashboard_card` pattern exactly. This is itself the third
straight dashboard-cards-route slice (POST, GET, PATCH, now DELETE) to
land clean on the first no-slop pass once test-writer-first + an
existing sibling-route pattern to mirror were both in place — not a new
pattern to promote, but a continued confirmation that this loop's
existing shape (brief → test-writer from the brief → implement against
a named sibling route → no-slop → real-server proof) is working as
designed for this file's routes.

## The next smallest slice

`POST /api/cards/{id}/run` — re-execute exactly one card's stored
`sql_text` (validate + execute, same as `GET /api/dashboards/{id}`'s
per-card re-execution, but scoped to one card without fetching the
whole dashboard) — the last remaining M6 card-actions backend endpoint
per PRD.md §8, flagged as a separate slice by both this and the prior
brief's Out-of-scope notes.
