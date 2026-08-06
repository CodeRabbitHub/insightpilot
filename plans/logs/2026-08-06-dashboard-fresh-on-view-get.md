# Slice log — dashboard-fresh-on-view-get

Date: 2026-08-06
Brief: plans/briefs/2026-08-06-dashboard-fresh-on-view-get.md

## The plan you approved
Add `GET /api/dashboards/{id}` to `app/main.py`: 404 if the dashboard
doesn't exist, else return its own fields plus every pinned
`DashboardCard` ordered by `position`, each re-validated and re-executed
fresh via `app/pipeline/answer.py`'s `_validate_and_execute` (no
`repair_sql()`, no LLM call, no new pool) — proving PRD F6/§8's
"fresh on view" for real. Any one card failing validation/execution 502s
the whole request rather than dropping it silently.

## The diff you accepted
Commit `8da3f8c` — "Add GET /api/dashboards/{id} with fresh-on-view card
re-execution." Full mechanics in `plans/logs/_auto-capture.md`'s
2026-08-06 18:58 entry: `app/main.py` +63/-1 (two new response models —
`DashboardCardWithRows`, `DashboardDetail` — plus the `get_dashboard`
route), `tests/test_api_dashboard_cards.py` +435 (four new test classes),
plus the brief file, the gate record, and a `templates/no-slop.md`
addition (see below).

## The done-check output
```
$ .venv/Scripts/python -m unittest discover -s tests -p "test_api_dashboard_cards.py" -v
... (31 tests: 12 pre-existing POST-route tests + 19 new GET-route tests) ...
----------------------------------------------------------------------
Ran 31 tests in 6.017s

OK
```
Full transcript and the real-`uvicorn`/`curl` shipping proof (pin →
fresh GET with real `rows` → unknown-id 404 → schema-drift 502 → cleanup)
are in `artifacts/reviews/2026-08-06-dashboard-fresh-on-view-get.md`.

## One thing you rejected or changed
The dev Postgres container was down at the start of this session (a
carried-over environment state, not something this slice's diff caused):
the done-check and the project's own `stop_verify` hook both failed with
`ConnectionRefusedError`/`psycopg2.OperationalError` on port 5433 because
Docker Desktop's daemon wasn't running at all. Fixed by starting Docker
Desktop and `docker compose up -d`, then re-ran everything fresh — not by
touching any test or the code under test. Confirmed root cause by
re-running the exact same suite twice: failing before the db was up,
passing immediately after, with the diff itself unchanged throughout.

Separately, a `stop_verify` run mid-session also flagged
`test_wire_analyze_answer.py` failing on a `VoyageAI`
`RemoteDisconnected` error — a transient network blip to an external
embeddings API, in a file this slice's diff never touches. Confirmed
transient (not a regression) by re-running that file alone once the
Postgres fix was in: 13/13 passed clean.

On the no-slop side: the second occurrence of "404 raised inside an open
`async with session:` block" (see below) was resolved by changing
`templates/no-slop.md`, not the code — the code already matches the
brief's explicitly named mirror target (`get_conversation`) and, on
inspection, is actually the codebase's majority shape already
(`get_conversation`, `create_dashboard_card`, now `get_dashboard`); only
`post_conversation_message` closes the session first, for its own
LLM-streaming-specific reason. The checklist was out of date, not the
code.

**Pattern promoted**: per HANDOFF.md's own ratchet rule ("promote if it
recurs"), `templates/no-slop.md` category 7 gained a line documenting
raise-inside-open-session as the accepted norm in this file, so future
no-slop passes stop re-flagging it as a deviation.

## The next smallest slice
`PATCH /api/cards/{id}` (rename/reposition an existing pinned card) —
the next-smallest write path on the dashboard-cards surface, needed
before any frontend "Pin"/dashboard grid work can let a user reorganize
what's already pinned.
