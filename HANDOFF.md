# Handoff

Date: 2026-08-06
Slice just completed: plans/briefs/2026-08-06-dashboard-fresh-on-view-get.md
  + plans/logs/2026-08-06-dashboard-fresh-on-view-get.md
  (commit 8da3f8c, capture c94c5c9)

## State of the work

- **`app/main.py` gains `GET /api/dashboards/{dashboard_id}`**: 404s with
  `{"detail": "dashboard not found"}` if the id doesn't exist; otherwise
  returns the dashboard's own fields (`id`, `name`, `created_at`) plus
  every pinned `DashboardCard` under it, ordered by `position` ascending
  — proven against out-of-order insertion, not just insertion/id order.
- Each returned card carries the persisted fields
  (`id`, `dashboard_id`, `title`, `question_text`, `sql_text`,
  `chart_spec_json`, `position`, `created_at`) plus a fresh `rows` field,
  obtained by re-validating (sqlglot via `app.catalog.sync.connect()`)
  and re-executing (the read-only asyncpg pool) that card's persisted
  `sql_text` on every single request — reusing
  `app/pipeline/answer.py`'s `_validate_and_execute(sql)` directly, no
  `repair_sql()`, no LLM call. `chart_spec_json` is returned unchanged,
  exactly as pinned. Proven fresh-not-cached by asserting the response's
  `rows` for one card match an independent, separately-invoked
  `execute_sql()` call on the same `sql_text`.
- If any one card's `sql_text` now fails validation or execution (e.g.
  schema drift since it was pinned), the *whole* request fails with 502
  (`HTTPException(status_code=502, detail=str(exc))`, matching `/api/ask`'s
  upstream-pipeline-failure convention) — never a 200 with that card
  silently dropped, proven by a test that deliberately pins a card
  referencing a nonexistent table and asserts both the 502 and the
  absence of any `cards` field in that error body.
- Two new Pydantic models back it: `DashboardCardWithRows` (extends the
  existing `DashboardCardDetail` with `rows: list[dict[str, Any]]`) and
  `DashboardDetail` (`id`, `name`, `created_at`, `cards`).
- **No new pool, no new dependency**: the app-schema read
  (`Dashboard`/`DashboardCard` via `async_session_factory`) is fully
  closed out before any card's SQL is validated/executed, so it never
  overlaps with the two SQL pools `_validate_and_execute()` uses.
  Existing `POST /api/dashboards/{id}/cards` is completely untouched.
- **`tests/test_api_dashboard_cards.py` gains 19 new tests** (31 total in
  the file) across four classes: happy path (ordering + freshness proof,
  ≥2 cards inserted out of position order), zero-own-cards (the
  empty-list code path, without asserting exact global emptiness since
  the seeded Overview dashboard is shared with concurrently-running
  suites), unknown-id 404, and deliberately-broken-SQL 502. Every test
  that creates a `DashboardCard` cleans it up; none ever deletes the
  seeded Overview dashboard row itself.
- **Gate 2 all five checks green** (full record:
  `artifacts/reviews/2026-08-06-dashboard-fresh-on-view-get.md`).
  No-slop review's one finding — the 404 raised inside an open
  `async with session:` block, the second occurrence of a shape flagged
  as a stylistic deviation in the prior slice — was resolved by fixing
  `templates/no-slop.md` itself (category 7 gained a line), not the
  code: on inspection this is already the codebase's majority shape
  (`get_conversation`, `create_dashboard_card`, now `get_dashboard`);
  only `post_conversation_message` closes the session first, for an
  LLM-streaming-specific reason of its own. Future no-slop passes should
  no longer flag raise-inside as a deviation.
- **Shipping proof went beyond `TestClient`**: a real `uvicorn` dev
  server was started and hit with real `curl` — pinned a real card,
  GET'd it back with real `rows` (`select count(*) from olist.orders`
  → `{"count":99441}`), confirmed 404 on an unknown id, pinned a second
  card referencing a nonexistent table and confirmed the GET now 502s
  the whole request, then deleted both proof cards and confirmed the
  Overview dashboard renders clean (`cards: []`) again.
- **Environment note, not a code issue**: the dev Postgres container
  was down at the start of this session (Docker Desktop's daemon
  wasn't running at all) — every test failure traced to
  `ConnectionRefusedError`/`OperationalError` on port 5433. Fixed by
  starting Docker Desktop and `docker compose up -d`; confirmed root
  cause by re-running the identical suite before/after with the diff
  itself unchanged. A separate mid-session `stop_verify` failure in
  `test_wire_analyze_answer.py` (a file this slice never touches) was a
  transient `VoyageAI` `RemoteDisconnected` network blip, confirmed
  transient by re-running that file alone afterward (13/13 passed).

## Proof

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
test_502_response_body_has_a_detail_string ... ok
test_502_response_body_has_no_cards_field ... ok
test_returns_502_not_200 ... ok
test_cards_are_ordered_by_position_ascending_not_insertion_order ... ok
test_each_card_echoes_its_persisted_fields_unchanged ... ok
test_every_card_in_the_response_has_exactly_the_persisted_fields_plus_rows ... ok
test_response_has_exactly_the_dashboard_level_fields ... ok
test_response_id_and_name_match_the_seeded_overview_dashboard ... ok
test_response_includes_both_cards_this_test_pinned ... ok
test_rows_field_is_a_nonempty_list_of_dicts ... ok
test_rows_match_an_independent_real_execute_sql_call_on_the_same_sql_text ... ok
test_cards_field_is_a_list ... ok
test_404_response_body_has_a_detail_string ... ok
test_persists_no_dashboard_card_rows_for_that_dashboard_id ... ok
test_returns_404 ... ok

----------------------------------------------------------------------
Ran 31 tests in 6.017s

OK
```

Real-server shipping proof (independent of `TestClient`):
```
=== POST a real card onto Overview (dashboard 1) ===
HTTP 200: {"id":399,...,"sql_text":"select count(*) from olist.orders",...}

=== GET /api/dashboards/1 ===
HTTP 200: {"id":1,"name":"Overview",...,"cards":[{"id":399,...,"rows":[{"count":99441}]}]}

=== GET /api/dashboards/999999999 ===
HTTP 404: {"detail":"dashboard not found"}

=== POST a card with broken SQL (select * from nonexistent_table) ===
HTTP 200 (pin succeeds -- storage is opaque)

=== GET /api/dashboards/1 (now with the broken card pinned) ===
HTTP 502: {"detail":"unknown table(s) referenced: olist.nonexistent_table"}
```
Both proof cards deleted afterward; Overview dashboard confirmed still
present and clean (`cards: []`).

## Open questions / known issues

- Carried over, unchanged from the previous handoff (still true, still
  unaddressed):
  - Frontend unit tests still exist but cannot execute — no
    vitest/jest wired into `web/package.json`. Adding one is a new
    dependency.
  - `chart_spec` still has no fixed schema by design
    (`prompts/analyze.md`); `ChartView.tsx`'s alias-resolution approach
    remains the frontend's answer to this.
  - ECharts auto-hides overlapping x-axis category labels under the
    `max-w-2xl` container width — not a bug, unaddressed by design.
  - No charting library styling beyond a single fixed accent color; no
    dark mode; no table-view toggle.
  - Decimal-valued rows still serialize as JSON strings, not numbers,
    in the raw `<pre>` dump.
  - `NullPool` needs re-evaluation under uvicorn's single persistent
    event loop — still flagged in `app/db/session.py`'s own comment.
  - What happens to an already-computed answer when its persistence
    write fails: still a plain 500 / silently truncated SSE stream.
  - `plans/logs/_auto-capture.md` remains silently uncommitted across
    every commit (pre-existing workflow gap, by design of the capture
    hook's timing) — also true of this handoff's own `HANDOFF.md`
    rewrite until the next slice's commit picks it up.
  - `tests/test_seed_idempotency.py`'s own real Postgres deadlock
    (M1-era, unrelated code) remains uninvestigated.
  - Lint/type tooling on the Python side (`ruff`, `mypy`) remains
    unaddressed.
  - A `response.content[0].text`/`ThinkingBlock` bug pattern is fixed
    only in `analyze_answer.py`; `generate_sql.py`, `repair_sql.py`,
    `describe.py` still carry the same fragile assumption.
  - The project's own `.venv` (Python 3.11.15) must be used explicitly
    for backend commands.
  - API base URL is a hardcoded `http://localhost:8000` constant in
    `web/src/api.ts`.
  - `Conversation`'s `user_id` FK to `users` is deliberately omitted —
    `users` doesn't exist yet (F8).
  - `queries` table (PRD §7's fourth `app`-schema table) still doesn't
    exist — not needed until the pipeline-logging slice.
  - `DELETE /api/cards/{id}`, `POST /api/cards/{id}/run`, and any
    frontend "Pin" button/dashboard grid still don't exist — later
    slices.
- New this session: Docker Desktop's daemon does not auto-start with
  this machine/session — if the next session's done-check fails with a
  Postgres connection refusal on port 5433, start Docker Desktop and run
  `docker compose up -d` before assuming a code regression.

## Next slice (the brief, written NOW while context is hot)

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
