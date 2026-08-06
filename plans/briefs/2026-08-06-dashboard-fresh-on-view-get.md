# Brief — dashboard-fresh-on-view-get

Date: 2026-08-06
Milestone: M6 Dashboard (fresh-on-view re-execution)

Goal:
Add `GET /api/dashboards/{id}` to `app/main.py`: returns the dashboard
(`id`, `name`, `created_at`) plus its pinned cards ordered by
`position`, where each card's persisted `sql_text` is re-validated
(sqlglot) and re-executed (the read-only pool) fresh on every call, with
the card returned carrying those fresh `rows` (`chart_spec_json`
returned unchanged, as originally pinned); 404s if the dashboard id
doesn't exist. Proves PRD F6/§8's "fresh on view" requirement for real,
against the live dev Postgres.

Constraints:
- Reuse the exact validate-then-execute sequence
  `app/pipeline/answer.py`'s `_validate_and_execute(sql)` already
  implements (owner-role sqlglot validation via `app.catalog.sync.connect()`
  + `app.pipeline.validate_sql.validate_sql()`, then
  `app.pipeline.execute_sql.execute_sql()`'s read-only pool) per card —
  call it or mirror it directly. Do NOT call `repair_sql()` and do NOT
  make any LLM call: fresh-on-view re-runs already-generated SQL, it
  never regenerates it. This matches ARCHITECT.md's two-pool,
  defense-in-depth decisions — no new pool, no new dependency.
- If any single card's SQL now fails validation or execution (e.g.
  schema drift since it was pinned), the whole request fails with 502
  (matching `/api/ask`'s existing upstream-pipeline-failure convention:
  `HTTPException(status_code=502, detail=str(exc))`) rather than
  silently omitting that card or serving stale/partial data. Per-card
  partial-failure rendering is explicitly out of scope this slice.
- `app/db/session.py`'s `async_session_factory` is the only thing used
  to read `Dashboard`/`DashboardCard` rows — never merged with the two
  SQL pools above.
- Cards must be ordered by their persisted `position` ascending in the
  response.
- Existing `POST /api/dashboards/{id}/cards` (`app/main.py`) is
  untouched — this slice only adds the GET route and its two new
  response models.

Inputs:
- PRD.md §8 (`GET /api/dashboards/{id} → cards with fresh data`), F6.
- `app/pipeline/answer.py`'s `_validate_and_execute(sql)` — the pattern
  to reuse per card, without its enclosing repair-loop machinery.
- `app/db/models.py`'s `Dashboard`/`DashboardCard` models.
- `app/main.py`'s `get_conversation` (existence-check-then-404, then
  building a parent-plus-children response) as the closest existing
  shape for a "one row + its ordered children" GET endpoint; `ask`'s
  try/except→502 shape for the failure path.
- `tests/test_api_dashboard_cards.py`'s `TestClient`/real-DB pattern and
  `test_app_db.py`'s `_get_overview_dashboard_ids()` /
  `_delete_dashboard_card()` helpers, extended in place (this stays one
  file — it's the same dashboard-cards surface as the POST route
  already there, not a new domain).

Outputs:
- `app/main.py` gains:
  - `DashboardCardWithRows` response model: the persisted card fields
    (`id`, `dashboard_id`, `title`, `question_text`, `sql_text`,
    `chart_spec_json`, `position`, `created_at`) plus fresh
    `rows: list[dict[str, Any]]`.
  - `DashboardDetail` response model: `id`, `name`, `created_at`,
    `cards: list[DashboardCardWithRows]`.
  - `GET /api/dashboards/{dashboard_id}` route implementing the above.
- `tests/test_api_dashboard_cards.py` gains a new test class (or
  classes) covering:
  - Happy path: pin ≥1 real card (reusing the existing pin helper/
    payload shape), call the new GET, assert the returned `rows` for
    that card match a real independently-executed
    `app.pipeline.execute_sql.execute_sql()` call on the same
    `sql_text` — proving "fresh," not stale/cached — and assert card
    ordering by `position` with ≥2 cards.
  - Unknown dashboard id (`999_999_999`) → 404.
  - A pinned card whose `sql_text` is (deliberately, in the test)
    invalid/unexecutable → the whole `GET` request 502s, not a
    partial/degraded 200.
  - Cleans up every card it creates; never deletes the seeded Overview
    dashboard row itself.

Done-check:
`.venv/Scripts/python -m unittest discover -s tests -p "test_api_dashboard_cards.py" -v`
passing, pasted fresh.

Out-of-scope:
- `PATCH /api/cards/{id}` (rename/position) and `DELETE /api/cards/{id}`
  — later slices.
- `POST /api/cards/{id}/run` (re-execute exactly one card) — later
  slice; this slice's GET already re-executes every card, so a
  single-card variant is separate, smaller work.
- Per-card partial failure / degraded rendering (a bad card fails the
  whole request this slice; graceful per-card error surfacing is a
  later slice's concern).
- `POST /api/dashboards` (creating additional dashboards) — PRD F6 is
  "one default dashboard" for v1; only the seeded Overview exists.
- Any frontend dashboard page/grid/Pin button.
- Auto-computed `position`/ordering changes.
