# Brief — delete-dashboard-card-endpoint

Date: 2026-08-07
Milestone: M6 Dashboard (card actions: rename, delete, open originating chat)

Goal:
Add `DELETE /api/cards/{card_id}` to `app/main.py`: deletes an existing
`DashboardCard` row by id and returns 204 with no body; 404s if the card
id doesn't exist.

Constraints:
- Deletes exactly one `DashboardCard` row, identified by `card_id` in the
  URL path — no request body, no query parameters.
- 204 No Content on success (no response body, distinct from every other
  route in this file, which all return 200 with a JSON body) — 404 with
  `{"detail": "card not found"}` (matching `patch_dashboard_card`'s exact
  message) if the id doesn't exist, with zero writes in that case.
- Only the `DashboardCard` row itself is removed. The parent `Dashboard`
  row is never touched or deleted by this route, regardless of whether
  the deleted card was its last remaining card.
- No new pool, no new dependency: `app/db/session.py`'s
  `async_session_factory` only, exactly like every other dashboard-cards
  route in this file.
- Existing `POST /api/dashboards/{id}/cards`, `GET /api/dashboards/{id}`,
  and `PATCH /api/cards/{id}` are untouched.

Inputs:
- PRD.md §8 (`DELETE /api/cards/{id}`), §6 ("Card actions: rename,
  delete, open originating chat").
- `app/main.py`'s `patch_dashboard_card` (existence-check-then-404 via
  `session.get(DashboardCard, card_id)`, same 404 message shape) as the
  closest existing pattern — here `session.delete(card)` +
  `session.commit()` instead of mutate-and-return.
- `tests/test_app_db.py`'s `_create_dashboard_card()`/
  `_delete_dashboard_card()` helpers and
  `tests/test_api_dashboard_cards.py`'s `TestClient`/real-DB pattern,
  extended in place — same dashboard-cards surface, not a new domain.
  Note `_delete_dashboard_card()` already exists as a test helper (used
  for cleanup by every prior test in this file) — this brief adds the
  real HTTP route, a distinct thing from that helper.

Outputs:
- `app/main.py` gains the `DELETE /api/cards/{card_id}` route (no new
  Pydantic model needed — no request body, no meaningful response body).
- Test coverage (extend `tests/test_api_dashboard_cards.py`): happy path
  (204 status, empty body, row genuinely gone via a fresh
  `async_session_factory` query — not just trusting the response),
  unknown card id (404, zero writes, matching this file's existing
  404-body convention), and deleting one card leaves its sibling cards
  under the same dashboard (and the dashboard row itself) untouched.

Done-check:
`.venv/Scripts/python -m unittest discover -s tests -p "test_api_dashboard_cards.py" -v`
passing, pasted fresh.

Out-of-scope:
- `POST /api/cards/{id}/run` (re-execute exactly one card without
  fetching the whole dashboard) — separate slice.
- Cascading deletes of a `Dashboard` and all its cards — not requested
  by PRD.md §8, which only lists a single-card `DELETE`.
- Any frontend delete button / confirmation UI.
- Bulk/multi-card delete (a single request removing several cards at
  once) — this slice is one card, one `DELETE`.
