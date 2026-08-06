# Brief — pin-dashboard-card-endpoint

Date: 2026-08-06
Milestone: M6 Dashboard (pin answers, responsive card grid, fresh-on-view)

Goal:
Add `POST /api/dashboards/{id}/cards` to `app/main.py`: given a dashboard
id and a card payload (title, question_text, sql_text, chart_spec_json,
position), create one `DashboardCard` row under that dashboard and return
it; 404 immediately (zero DB writes) if the dashboard id doesn't exist —
proven by a real HTTP round-trip against the real dev Postgres.

Constraints:
- Reuse `app/db/session.py`'s existing `async_session_factory` — no new
  pool, no new dependency.
- Mirror `app/main.py`'s existing endpoint conventions exactly:
  `post_conversation_message`'s "check existence, then 404 with zero
  side effects" pattern for the unknown-id case; `create_conversation`'s
  "insert via ORM, flush, commit, return" pattern for the happy path.
- The request body supplies all five card fields explicitly (title,
  question_text, sql_text, chart_spec_json, position) — this slice does
  not auto-compute `position`/ordering or re-execute `sql_text`; it
  trusts the caller (the future frontend "Pin" button, which will
  already hold an answered chat message's SQL/chart spec/question in
  hand) and stores exactly what's given.
- No SQL execution or sqlglot validation at pin time — `sql_text` is
  stored as an opaque string. Validation/execution belongs to the
  fresh-on-view `GET /api/dashboards/{id}` endpoint (a later slice),
  which is where CLAUDE.md's "generated SQL executes only through the
  read-only pool, only after sqlglot validation" rule actually applies
  (this endpoint never executes anything).
- Response model returns the created card's `id`, `dashboard_id`,
  `title`, `question_text`, `sql_text`, `chart_spec_json`, `position`,
  `created_at` — mirrors `ConversationDetail`/`MessageDetail`'s style of
  a plain Pydantic response model over the ORM row.
- Real HTTP test via `fastapi.testclient.TestClient` against the real
  dev Postgres (no mocking the DB) — matches
  `tests/test_api_conversations.py`'s established convention. No LLM
  call is involved in this endpoint, so no `setUpClass`-shared-billed-
  request pattern is needed here.

Inputs:
- PRD.md §8 (`POST /api/dashboards/{id}/cards → pin`).
- `app/main.py` — `create_conversation` (simple insert-and-return
  pattern) and `post_conversation_message` (existence-check-then-404
  pattern) as the two patterns to combine.
- `app/db/models.py` — this slice's `Dashboard`/`DashboardCard` models.
- `tests/test_api_conversations.py` — the `TestClient`-based endpoint
  test pattern (happy path + unknown-id 404 path, DB assertions via
  `async_session_factory`) to mirror for the pin endpoint.
- `tests/test_app_db.py`'s `_get_overview_dashboard_ids()` /
  `_delete_dashboard_card()` helpers — reusable for locating the seeded
  Overview dashboard and cleaning up test-created cards.

Outputs:
- `app/main.py` gains a `CreateDashboardCardRequest` Pydantic model, a
  `DashboardCardDetail` response model, and the
  `POST /api/dashboards/{id}/cards` route.
- `tests/test_api_dashboard_cards.py` (new file): a real `TestClient`
  round-trip — pin a card under the seeded Overview dashboard, assert
  the response shape and a 200/201, assert the row exists via
  `async_session_factory`, clean it up; plus an unknown-dashboard-id
  test asserting 404 and zero rows written.

Done-check:
`python -m unittest discover -s tests -p "test_api_dashboard_cards.py" -v`
passing, pasted fresh.

Out-of-scope:
- `GET /api/dashboards/{id}` (fresh-on-view re-execution) — needs
  `execute_sql()`/sqlglot wiring, a separate slice.
- `PATCH /api/cards/{id}` (rename/position) and `DELETE /api/cards/{id}`
  — later slices.
- `POST /api/cards/{id}/run` (re-execute one card) — later slice.
- Any frontend "Pin" button or dashboard page/grid.
- Auto-computed `position`/ordering logic.
- `queries` table, `users` table/auth (unrelated milestones).
