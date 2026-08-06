# Slice log — dashboard persistence foundation

Date: 2026-08-06
Brief: plans/briefs/2026-08-06-dashboard-persistence.md

## The plan you approved

Chain a new Alembic migration off the existing `f2f458dd2525` head to
create `app.dashboards` and `app.dashboard_cards` (mirroring that
migration's `op.create_table(..., schema="app")` style exactly), seed
one `Overview` row via `op.execute`, add matching `Dashboard`/
`DashboardCard` ORM models to `app/db/models.py`, and have the
test-writer subagent extend `tests/test_app_db.py` with a round-trip
test from the brief alone, before any implementation existed.

## The diff you accepted

`c6e267d` — Add dashboards/dashboard_cards schema, ORM models, and
seeded Overview row (5 files, +502/-2: new migration, `app/db/models.py`
+25, `tests/test_app_db.py` +226, brief + gate record). Full mechanics in
`plans/logs/_auto-capture.md`.

## The done-check output

```
$ .venv/Scripts/alembic upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
(exit code 0)

$ .venv/Scripts/python -m unittest discover -s tests -p "test_app_db.py" -v
Ran 13 tests in 4.712s

OK
```
Full check-by-check record: `artifacts/reviews/2026-08-06-dashboard-persistence.md`
(includes a fifth-check direct-`asyncpg` query against the real dev
Postgres, independent of the ORM/test layer, confirming both tables'
exact column types and the seeded Overview row).

## One thing you rejected or changed

The new migration's `downgrade()` docstring enumerated the `app`
schema's current tenant tables by name ("conversations/messages and
catalog_tables/catalog_columns/kb_chunks") — the *third* time this
project has hit the enumerated-list-goes-stale shape (1st: the
`asAssistantContent()` doc comment naming `ChartView`, then `ChartView
and SqlDetails`; 2nd was that same line's second edit, which is what got
it promoted into `templates/no-slop.md` §6 in the last slice's capture).
This time the no-slop-reviewer subagent caught it on its own, unprompted
— because §6 already exists — rather than needing a human to notice
again. That's the ratchet working as designed: no further promotion
needed this round, just the fix (generalized to "other tables already
live in it and predate this migration" so the next `app`-schema table,
e.g. `queries`, can't make it stale again).

## The next smallest slice

Wire the dashboard API endpoints (`GET /api/dashboards/{id}` with
fresh-on-view re-execution, `POST /api/dashboards/{id}/cards` to pin,
`PATCH /api/cards/{id}` for rename/position) on top of this slice's
models.
