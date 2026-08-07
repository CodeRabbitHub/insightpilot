# Handoff

Date: 2026-08-07
Slice just completed: plans/briefs/2026-08-07-delete-dashboard-card-endpoint.md
  + plans/logs/2026-08-07-delete-dashboard-card-endpoint.md
  (commit 2097aa5)

## State of the work

- **`app/main.py` gains `DELETE /api/cards/{card_id}`**: deletes exactly
  one existing `DashboardCard` row by id and returns 204 with no
  response body — the first 204 route in this file (every other route
  returns 200 with a JSON body). 404s with `{"detail": "card not
  found"}` (matching `patch_dashboard_card`'s exact message) if the card
  id doesn't exist, with zero writes in that case. Only the
  `DashboardCard` row is removed; the parent `Dashboard` row is never
  touched, regardless of whether the deleted card was its last one.
- **No new Pydantic model, no new pool, no new dependency**: same
  `async_session_factory` used by every other dashboard-cards route;
  existing `POST /api/dashboards/{id}/cards`, `GET /api/dashboards/{id}`,
  and `PATCH /api/cards/{id}` are completely untouched.
- **`tests/test_api_dashboard_cards.py` gains 3 new test classes** (10
  new test methods, 64 total in the file): happy path (204, empty body,
  row genuinely gone via a fresh `async_session_factory` query — not
  just trusting the response), unknown id (404, exact
  `{"detail":"card not found"}` body, no phantom row), and sibling
  isolation (deleting one card leaves a sibling card under the same
  dashboard, and the dashboard row itself, completely untouched).
- **Gate 2 all five checks green** (full record:
  `artifacts/reviews/2026-08-07-delete-dashboard-card-endpoint.md`).
  No-slop review returned zero findings across all 10 categories on the
  first pass — third straight dashboard-cards-route slice to land clean
  first-pass once test-writer-first + a named sibling route to mirror
  were both in place.
- **Shipping proof went beyond `TestClient`**: a real `uvicorn` dev
  server was started and hit with real `curl` — posted a real card (id
  1187), confirmed it present via `GET /api/dashboards/1`, `DELETE`d it
  (204, empty body), confirmed via a fresh `GET /api/dashboards/1` that
  it no longer appears while sibling cards remain, then `DELETE`d an
  unknown id (404, exact detail body). Dev server process stopped
  afterward, confirmed via a follow-up request refusing the connection.

## Proof

```
$ .venv/Scripts/python -m unittest discover -s tests -p "test_api_dashboard_cards.py" -v
...
----------------------------------------------------------------------
Ran 64 tests in 16.708s

OK
```

Real-server shipping proof (independent of `TestClient`):
```
=== POST a real proof card onto Overview (dashboard 1) ===
{"id":1187,"dashboard_id":1,"title":"Delete-proof card",...,"position":77,...}

=== GET dashboard 1 before DELETE - confirm proof card is present ===
[957, 948, 949, 950, 951, 953, 955, 1187]

=== DELETE the proof card ===
HTTP/1.1 204 No Content
(empty body)

=== GET dashboard 1 after DELETE - confirm proof card is gone, dashboard survives ===
dashboard id: 1 name: Overview card ids: [948, 949, 950, 951, 953, 955, 957]

=== DELETE an unknown card id ===
HTTP/1.1 404 Not Found
{"detail":"card not found"}
```

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
  - Any frontend "Pin"/card-actions UI (rename input, delete button,
    drag-to-reposition) still doesn't exist — later slices.
  - Docker Desktop's daemon does not auto-start with this
    machine/session — if the next session's done-check fails with a
    Postgres connection refusal on port 5433, start Docker Desktop and
    run `docker compose up -d` before assuming a code regression.
  - The dev Postgres `dashboards`/`dashboard_cards` tables have
    accumulated leftover proof/test cards from prior sessions' real-
    server shipping proofs (ids in the 940s-1180s range under the
    seeded Overview dashboard) — harmless (every test scopes its
    assertions to the specific ids it created, per this file's
    established convention) but worth a cleanup pass eventually.

## Next slice (the brief, written NOW while context is hot)

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
  already calls per-card — not a hand-rolled validate/execute path.
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
