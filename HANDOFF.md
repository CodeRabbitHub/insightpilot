# Handoff

Date: 2026-08-06
Slice just completed: plans/briefs/2026-08-06-pin-dashboard-card-endpoint.md
  + plans/logs/2026-08-06-pin-dashboard-card-endpoint.md
  (commit 089c0d4, capture 5780d7c)

## State of the work

- **`app/main.py` gains `POST /api/dashboards/{dashboard_id}/cards`**:
  given a JSON body of `title`, `question_text`, `sql_text`,
  `chart_spec_json`, `position`, it creates one `DashboardCard` row
  under `dashboard_id` and returns it (`id`, `dashboard_id`, `title`,
  `question_text`, `sql_text`, `chart_spec_json`, `position`,
  `created_at`); 404s with `{"detail": "dashboard not found"}` and zero
  DB writes if `dashboard_id` doesn't refer to a real `Dashboard` row.
- Two new Pydantic models back it: `CreateDashboardCardRequest` (the
  request body) and `DashboardCardDetail` (the response), following
  this file's existing `*Request`/`*Detail` naming.
- Implementation mirrors two existing patterns exactly:
  `create_conversation`'s insert-flush-commit-return shape, and
  `post_conversation_message`'s check-existence-then-404-with-zero-writes
  shape (`session.get(Dashboard, dashboard_id)` before ever constructing
  the new row).
- **No new pool, no new dependency, no SQL execution/sqlglot
  validation at pin time** — `sql_text` is stored as an opaque string,
  per the brief's Constraints; validation/execution is deferred to the
  not-yet-built fresh-on-view `GET /api/dashboards/{id}` endpoint.
- **`tests/test_api_dashboard_cards.py` (new, 12 tests)**: a real
  `fastapi.testclient.TestClient` round-trip against the real dev
  Postgres (no mocking) — happy path pins a card under the seeded
  Overview dashboard, asserts the exact 8-field response shape
  (including a nested `chart_spec_json` dict round-tripping unchanged),
  asserts the row is visible in a brand-new session, cleans up, and
  confirms the Overview dashboard itself survives; a second test class
  asserts an unknown sentinel dashboard id (`999_999_999`) 404s with
  zero `DashboardCard` rows written.
- **Gate 2 all five checks green** (full record:
  `artifacts/reviews/2026-08-06-pin-dashboard-card-endpoint.md`). No-slop
  review surfaced two low-severity stylistic deviations from "mirror
  exactly" (response built right after `flush()` rather than after
  `commit()`; the 404 raised inside the session's `async with` block
  rather than after it closes) — both accepted as-is, proven harmless by
  the passing real-DB tests rather than just asserted. First occurrence
  of this exact shape; not yet promoted to `templates/no-slop.md` (see
  the slice log for the reasoning — promote if it recurs).
- **Shipping proof went beyond `TestClient`**: a real `uvicorn` dev
  server was started, hit with real `curl` POSTs (happy path returned a
  real card with a real `created_at` timestamp; unknown id returned a
  real 404), then the proof row was deleted and the Overview dashboard
  confirmed still present.

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
test_persists_no_dashboard_card_rows_for_that_dashboard_id ... ok
test_returns_404 ... ok

Ran 12 tests in 1.351s

OK
```

Real-server shipping proof (independent of `TestClient`):
```
=== POST /api/dashboards/1/cards (real uvicorn, real curl) ===
HTTP/1.1 200 OK
{"id":56,"dashboard_id":1,"title":"Gate shipping-proof card", ...,
 "created_at":"2026-08-06T07:08:17.990623Z"}

=== POST /api/dashboards/999999999/cards ===
HTTP/1.1 404 Not Found
{"detail":"dashboard not found"}
```

## Open questions / known issues

- The two accepted no-slop stylistic deviations above (build-before-
  commit; raise-404-inside-block) are a first occurrence — if a future
  slice's no-slop pass flags either shape again, promote it into
  `templates/no-slop.md` per the ratchet rule.
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
  - `PATCH /api/cards/{id}`, `DELETE /api/cards/{id}`,
    `POST /api/cards/{id}/run`, and any frontend "Pin" button/dashboard
    grid still don't exist — later slices.

## Next slice (the brief, written NOW while context is hot)

Goal:
Add `GET /api/dashboards/{id}` to `app/main.py`: returns the dashboard
(`id`, `name`, `created_at`) plus its pinned cards ordered by
`position`, where each card's persisted `sql_text` is re-validated
(sqlglot) and re-executed (the read-only pool) fresh on every call and
the card is returned with those fresh `rows` attached (`chart_spec_json`
returned unchanged, as originally pinned); 404s if the dashboard id
doesn't exist — proving PRD F6/§8's "fresh on view" requirement for
real, against the live dev Postgres.

Constraints:
- Reuse the exact validate-then-execute sequence
  `app/pipeline/answer.py`'s `_validate_and_execute(sql)` already
  implements (owner-role sqlglot validation via
  `app.catalog.sync.connect()`, then `execute_sql()`'s read-only pool)
  per card — call it or mirror it directly; do NOT call `repair_sql()`
  and do NOT make any LLM call. Fresh-on-view re-runs already-generated
  SQL; it never regenerates it.
- If any single card's SQL now fails validation or execution (e.g.
  schema drift since it was pinned), the whole request must fail
  clearly (502, matching `/api/ask`'s existing upstream-pipeline-failure
  convention) rather than silently omitting that card or serving
  stale/partial data. Per-card partial-failure rendering is explicitly
  out of scope this slice.
- No new pool, no new dependency: `app/db/session.py`'s
  `async_session_factory` for reading `Dashboard`/`DashboardCard` rows;
  `app/pipeline/validate_sql.py` + `app/pipeline/execute_sql.py`'s two
  existing pools (owner-role catalog connection, read-only asyncpg
  pool) for the fresh row fetch — never merged, never a new one.
- Cards must be ordered by their persisted `position` ascending in the
  response.

Inputs:
- PRD.md §8 (`GET /api/dashboards/{id} → cards with fresh data`), F6.
- `app/pipeline/answer.py`'s `_validate_and_execute(sql)` — the pattern
  to reuse per card, without its enclosing repair-loop machinery.
- `app/db/models.py`'s `Dashboard`/`DashboardCard` models.
- `app/main.py`'s `get_conversation` (existence-check-then-404, then
  building a parent-plus-children response) as the closest existing
  shape for a "one row + its ordered children" GET endpoint.
- `tests/test_api_dashboard_cards.py`'s `TestClient`/real-DB pattern and
  its `_get_overview_dashboard_ids()`/`_delete_dashboard_card()` helpers
  (from `tests/test_app_db.py`) to extend.

Outputs:
- `app/main.py` gains a `DashboardCardWithRows` (or similarly named)
  response model carrying the persisted card fields plus fresh `rows`,
  a `DashboardDetail` response model (`id`, `name`, `created_at`,
  `cards: list[...]`), and the `GET /api/dashboards/{id}` route.
- Test coverage (extend `tests/test_api_dashboard_cards.py` or add a
  new file — decide during `/brief`): a happy-path test that pins ≥1
  real card, calls the new GET, and asserts the returned `rows` match a
  real independently-executed SELECT (proving "fresh," not stale/cached
  data); an unknown-dashboard-id 404 test; and a test proving a card
  whose `sql_text` now fails validation/execution causes the whole
  request to fail with a clear 502, not a silently dropped card.

Done-check:
`python -m unittest discover -s tests -p "test_api_dashboard_cards.py" -v`
passing, pasted fresh (adjust the `-p` pattern if a new test file name
is chosen during `/brief`).

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
