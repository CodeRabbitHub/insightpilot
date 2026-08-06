# Slice log — patch-dashboard-card-endpoint

Date: 2026-08-06
Brief: plans/briefs/2026-08-06-patch-dashboard-card-endpoint.md

## The plan you approved

Add `PatchDashboardCardRequest` (`title: str | None`, `position: int |
None`, both defaulting to `None`) and a `PATCH /api/cards/{card_id}`
route to `app/main.py`, mirroring `create_dashboard_card`'s existing
existence-check-then-404 / flush-then-build-result-then-commit shape:
`session.get(DashboardCard, card_id)` → 404 if `None` → apply each
field only if `is not None` → return via the existing
`DashboardCardDetail` model. No new pool, no new dependency.

## The diff you accepted

Commit `69671ff` — "Add PATCH /api/cards/{id} for card rename/
reposition". `app/main.py` +38 lines (one model, one route);
`tests/test_api_dashboard_cards.py` +601 lines (7 new test classes: the
5 from the brief's Outputs plus 2 added during no-slop review, see
below). Full stat in `plans/logs/_auto-capture.md`'s "Commit at
2026-08-06 23:31" entry.

## The done-check output

```
.venv/Scripts/python -m unittest discover -s tests -p "test_api_dashboard_cards.py" -v
...
Ran 54 tests in 8.738s

OK
```
(54 = 24 pre-existing + 30 across the 7 new PATCH test classes; every
new test cleans up its own card via `_delete_dashboard_card`, none
touches the seeded Overview `dashboards` row.)

Shipping proof (real `uvicorn` dev server + real `curl`, not just
`TestClient`) — full transcript in
`artifacts/reviews/2026-08-06-patch-dashboard-card-endpoint.md`:
posted a real card (id 851), PATCHed it title-only / position-only /
both / empty-body (each 200, empty-body a true no-op), PATCHed an
unknown id (404 `{"detail":"card not found"}`), then deleted the proof
card and confirmed it no longer appears under `GET /api/dashboards/1`.

## One thing you rejected or changed

Two rounds of no-slop review found and fixed real test-coverage gaps —
not code bugs, but claims the implementation made that nothing proved:

1. **Pass 1** — no test PATCHed a falsy-but-meaningful new value
   (`position: 0`, `title: ""`) to prove the route's `is not None`
   checks (not a plain truthiness check) are what's actually running.
   A silent regression to truthiness checks would have shipped
   undetected. Fixed: added `PatchDashboardCardFalsyNewValuesTests`,
   seeding a card with non-falsy values and asserting both apply, via
   the response and a fresh DB session.
2. **Pass 2** (re-review after the pass-1 fix) — no test proved the
   brief's "sql_text/question_text/chart_spec_json/dashboard_id stay
   exactly as pinned" Constraint at the HTTP layer; it held only
   structurally (Pydantic silently drops the unknown keys, no
   `extra="forbid"` anywhere in the file). Fixed: added
   `PatchDashboardCardIgnoresDisallowedFieldsTests`, PATCHing a body
   with all four disallowed fields alongside a legitimate `title`
   change and asserting none of the four moved.

Both findings are `templates/no-slop.md`'s existing "Untested edges"
category (promoted from `2026-08-02-catalog-sync-cli.md`, already
confirmed working a second time in
`2026-08-05-conversations-read-endpoints.md`) — this is a third
confirmation of an already-standing rule, not a new pattern. No further
promotion made this slice.

## The next smallest slice

`DELETE /api/cards/{id}` — the smallest of the two remaining M6
card-actions endpoints (delete vs. re-run-one-card), removing a single
`DashboardCard` row by id and 404ing if it doesn't exist, per this
brief's own Out-of-scope note flagging it as "separate, smaller slice."
