# Brief — patch-dashboard-card-endpoint

Date: 2026-08-06
Milestone: M6 Dashboard (card actions: rename, delete, open originating chat)

Goal:
Add `PATCH /api/cards/{id}` to `app/main.py`: partially updates an
existing `DashboardCard`'s `title` and/or `position` — whichever of the
two the request body supplies, leaving any field it omits unchanged —
and returns the updated card; 404s if the card id doesn't exist. Per
PRD.md §8's `PATCH /api/cards/{id} → rename/position`.

Constraints:
- Only `title` and `position` are mutable via this endpoint. The
  request model must carry no field for `dashboard_id`, `question_text`,
  `sql_text`, or `chart_spec_json` — those stay exactly as pinned;
  renaming/repositioning never touches or re-validates `sql_text`.
- Partial update: both `title` and `position` are optional on the
  request; a field omitted (or explicitly `null`) from the request body
  leaves that column unchanged on the row. Supplying neither is a
  no-op 200 (returns the card unchanged) — do not treat an empty body
  as a 422; that's needless scope for a same-shape rename-only or
  position-only call to already need.
- Response model: reuse the existing `DashboardCardDetail` (the same 8
  persisted fields returned by `POST /api/dashboards/{id}/cards`) — no
  `rows`, since PATCH never executes `sql_text`.
- No new pool, no new dependency: `app/db/session.py`'s
  `async_session_factory` only, exactly like every other dashboard-cards
  route in this file.
- Existing `POST /api/dashboards/{id}/cards` and
  `GET /api/dashboards/{id}` are untouched.

Inputs:
- PRD.md §8 (`PATCH /api/cards/{id} → rename/position`), §6 ("Card
  actions: rename, delete, open originating chat").
- `app/main.py`'s `create_dashboard_card` (existence-check-then-404,
  build-then-flush-then-commit shape) as the closest existing pattern —
  here checking `DashboardCard` existence directly (there is no parent
  `dashboard_id` in the URL for this route), not `Dashboard`.
- `app/db/models.py`'s `DashboardCard` for the exact column set.
- `tests/test_api_dashboard_cards.py`'s `TestClient`/real-DB pattern and
  its `_create_dashboard_card()`/`_delete_dashboard_card()` helpers (from
  `tests/test_app_db.py`), extended in place — same dashboard-cards
  surface, not a new domain.

Outputs:
- `app/main.py` gains a `PatchDashboardCardRequest` request model
  (`title: str | None = None`, `position: int | None = None`) and the
  `PATCH /api/cards/{card_id}` route, reusing `DashboardCardDetail` as
  the response model.
- Test coverage (extend `tests/test_api_dashboard_cards.py`): rename
  only (position unchanged), reposition only (title unchanged), both
  together, an empty-body no-op (both fields unchanged, still 200), and
  an unknown card id → 404. Every test cleans up the card it creates;
  none deletes the seeded Overview dashboard row.

Done-check:
`.venv/Scripts/python -m unittest discover -s tests -p "test_api_dashboard_cards.py" -v`
passing, pasted fresh.

Out-of-scope:
- `DELETE /api/cards/{id}` — separate, smaller slice.
- `POST /api/cards/{id}/run` (re-execute exactly one card) — separate
  slice.
- Any validation, re-execution, or mutation of `sql_text`,
  `question_text`, `chart_spec_json`, or `dashboard_id` via this route —
  all remain immutable here.
- Bulk/multi-card reposition (e.g. a single request reordering an
  entire card list at once) — this slice is one card, one `PATCH`, per
  the brief's Goal.
- Any frontend card-actions UI (rename input, drag-to-reposition).
