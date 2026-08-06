# Handoff

Date: 2026-08-06
Slice just completed: plans/briefs/2026-08-06-patch-dashboard-card-endpoint.md
  + plans/logs/2026-08-06-patch-dashboard-card-endpoint.md
  (commit 69671ff)

## State of the work

- **`app/main.py` gains `PATCH /api/cards/{card_id}`**: partially
  updates an existing `DashboardCard`'s `title` and/or `position` —
  whichever the request body supplies. A field omitted, or explicitly
  `null`, leaves that column unchanged; an empty body `{}` is a 200
  no-op, proven not to be a 422. 404s with `{"detail": "card not
  found"}` if the card id doesn't exist. Response reuses the existing
  `DashboardCardDetail` model (no `rows` — this route never touches or
  re-validates `sql_text`).
- One new Pydantic model backs it: `PatchDashboardCardRequest`
  (`title: str | None = None`, `position: int | None = None`).
- **No new pool, no new dependency**: same `async_session_factory`
  used by every other dashboard-cards route; existing
  `POST /api/dashboards/{id}/cards` and `GET /api/dashboards/{id}` are
  completely untouched.
- **`tests/test_api_dashboard_cards.py` gains 7 new test classes** (30
  new test methods, 54 total in the file): rename-only, reposition-
  only, both-fields, empty-body-no-op, unknown-id-404, plus two added
  during no-slop review — falsy-new-values (`title:""`/`position:0`
  actually applied, not skipped as falsy) and ignores-disallowed-fields
  (`sql_text`/`dashboard_id`/`chart_spec_json`/`question_text` sent in
  the same body as a legitimate `title` change, proven to have zero
  effect). Every test cleans up its own card; none deletes the seeded
  Overview dashboard row.
- **Gate 2 all five checks green** (full record:
  `artifacts/reviews/2026-08-06-patch-dashboard-card-endpoint.md`). Two
  rounds of no-slop review both landed in the already-promoted
  "Untested edges" category (`templates/no-slop.md`, promoted from
  `2026-08-02-catalog-sync-cli.md`) — a third confirmation of that
  standing rule, not a new pattern; no further promotion made.
- **Shipping proof went beyond `TestClient`**: a real `uvicorn` dev
  server was started and hit with real `curl` — posted a real card
  (id 851), PATCHed it title-only/position-only/both/empty-body (each
  200, empty-body a true no-op returning the prior PATCH's values
  unchanged), PATCHed an unknown id (404, exact `"card not found"`
  detail), then deleted the proof card and confirmed via a fresh
  `GET /api/dashboards/1` that it no longer appears. Dev server process
  stopped afterward, confirmed via a follow-up request refusing the
  connection.

## Proof

```
$ .venv/Scripts/python -m unittest discover -s tests -p "test_api_dashboard_cards.py" -v
... (54 tests, including all pre-existing ones)
----------------------------------------------------------------------
Ran 54 tests in 8.738s

OK
```

Real-server shipping proof (independent of `TestClient`):
```
=== POST a real card onto Overview (dashboard 1) ===
HTTP 200: {"id":851,...,"title":"Proof card before PATCH",...,"position":42,...}

=== PATCH title only ===
{"id":851,...,"title":"Renamed by real PATCH",...,"position":42,...}

=== PATCH position only ===
{"id":851,...,"title":"Renamed by real PATCH",...,"position":0,...}

=== PATCH both ===
{"id":851,...,"title":"Both changed",...,"position":99,...}

=== PATCH empty body (no-op) ===
{"id":851,...,"title":"Both changed",...,"position":99,...}   <- unchanged

=== PATCH unknown id ===
HTTP 404: {"detail":"card not found"}
```
Proof card 851 deleted afterward; confirmed absent from a subsequent
`GET /api/dashboards/1`.

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
  - `POST /api/cards/{id}/run` (re-execute exactly one card) and any
    frontend "Pin"/card-actions UI (rename input, delete button,
    drag-to-reposition) still don't exist — later slices.
  - Docker Desktop's daemon does not auto-start with this
    machine/session — if the next session's done-check fails with a
    Postgres connection refusal on port 5433, start Docker Desktop and
    run `docker compose up -d` before assuming a code regression.

## Next slice (the brief, written NOW while context is hot)

Goal:
Add `DELETE /api/cards/{card_id}` to `app/main.py`: deletes an existing
`DashboardCard` row by id and returns 204 with no body; 404s if the
card id doesn't exist. Per PRD.md §8's `DELETE /api/cards/{id}` and
§6's "Card actions: rename, delete, open originating chat."

Constraints:
- Deletes exactly one `DashboardCard` row, identified by `card_id` in
  the URL path — no request body, no query parameters.
- 204 No Content on success (no response body, matching REST convention
  for DELETE and distinct from every other route in this file, which
  all return 200 with a JSON body) — 404 with `{"detail": "card not
  found"}` (matching `patch_dashboard_card`'s exact message) if the id
  doesn't exist, with zero writes in that case.
- Only the `DashboardCard` row itself is removed. The parent
  `Dashboard` row is never touched or deleted by this route, regardless
  of whether the deleted card was its last remaining card.
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
  Pydantic model needed — no request body, no meaningful response
  body).
- Test coverage (extend `tests/test_api_dashboard_cards.py`): happy
  path (204 status, empty body, row genuinely gone via a fresh
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
