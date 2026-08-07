# Brief — run-dashboard-card-endpoint

Date: 2026-08-07
Milestone: M6 Dashboard (card actions: rename, delete, open originating chat —
this route is re-run, PRD.md §8 `POST /api/cards/{id}/run`)

Goal:
Add `POST /api/cards/{card_id}/run` to `app/main.py`: re-validates and
re-executes exactly one existing `DashboardCard`'s stored `sql_text` and
returns its fresh rows, without fetching the rest of its dashboard.

Constraints:
- Takes `card_id` from the URL path only — no request body, no query
  parameters (the card's own stored `sql_text` is the only input to
  execution; nothing about it is overridable via this route).
- 404 with `{"detail": "card not found"}` (matching
  `patch_dashboard_card`/`delete_dashboard_card`'s exact message) if the
  card id doesn't exist, with zero validation/execution attempted in
  that case.
- Re-execution reuses `app/pipeline/answer.py`'s
  `_validate_and_execute(sql)` — the same function `get_dashboard`
  already calls per-card — not a hand-rolled validate/execute path. This
  keeps the sqlglot-parse-gate → read-only-pool defense chain
  (ARCHITECT.md) intact: no new SQL execution path, generated/stored SQL
  still only ever runs through that one function.
- If validation or execution fails (e.g. schema drift since the card
  was pinned), the route responds 502 with a `detail` string, matching
  `get_dashboard`'s existing upstream-pipeline-failure convention for
  the same failure class — not a 200 with an error payload, not a 500.
- Success response reuses the existing `DashboardCardWithRows` model
  (card's persisted fields + fresh `rows`) — no new Pydantic model.
- The app-schema read (fetching the `DashboardCard` row) must be closed
  out (session closed) before `_validate_and_execute` runs, exactly like
  `get_dashboard` already does, so the app pool never overlaps with the
  two SQL pools `_validate_and_execute` uses.
- No new pool, no new dependency: `app/db/session.py`'s
  `async_session_factory` only.
- Existing `POST /api/dashboards/{id}/cards`, `GET /api/dashboards/{id}`,
  `PATCH /api/cards/{id}`, and `DELETE /api/cards/{id}` are untouched.

Inputs:
- PRD.md §8 (`POST /api/cards/{id}/run`), §6 ("Card actions: rename,
  delete, open originating chat" — re-run is this route's analytics
  equivalent of "refresh this one card").
- `app/main.py`'s `get_dashboard` (per-card `_validate_and_execute` call,
  502-on-failure convention, session-closed-before-execution ordering)
  and `delete_dashboard_card`/`patch_dashboard_card` (existence-check-
  then-404 shape, exact 404 message) as the two patterns to combine.
- `app/pipeline/answer.py`'s `_validate_and_execute(sql)` — returns
  `(sql, rows)`; only `rows` is needed here.
- `tests/test_api_dashboard_cards.py`'s `_create_dashboard_card`/
  `_delete_dashboard_card`/`_fetch_card` helpers and `TestClient`/
  real-DB pattern, extended in place — same dashboard-cards surface.

Outputs:
- `app/main.py` gains the `POST /api/cards/{card_id}/run` route (reuses
  `DashboardCardWithRows`, no new Pydantic model).
- Test coverage (extend `tests/test_api_dashboard_cards.py`): happy path
  (200, response has the card's persisted fields plus fresh `rows`
  matching an independent `execute_sql`/`_validate_and_execute` call on
  the same `sql_text` — mirroring `DashboardDetailHappyPathTests`'s
  existing "rows match an independent real execution" pattern), unknown
  card id (404, exact detail body, zero validation/execution attempted
  — e.g. assert no exception path was hit some observable way, or at
  minimum that the response is the plain 404 and not a 502), and a bad
  `sql_text` on the card (502, `detail` string, no `rows` field) —
  mirroring `DashboardDetailBadCardSqlTests`.

Done-check:
`.venv/Scripts/python -m unittest discover -s tests -p "test_api_dashboard_cards.py" -v`
passing, pasted fresh.

Out-of-scope:
- Any frontend "refresh this card" button or UI.
- Overriding or editing `sql_text` as part of this call — re-execution
  only, no mutation (that's `PATCH /api/cards/{id}`'s job, and even it
  never touches `sql_text`).
- Re-running every card on a dashboard in one request — that's already
  `GET /api/dashboards/{id}`'s job; this route is deliberately one card.
- Caching or storing the fresh `rows` anywhere — same "no `rows` column
  to cache" reasoning as `GET /api/dashboards/{id}`.
