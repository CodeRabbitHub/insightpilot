# Review gate — dashboard persistence foundation

Date: 2026-08-06
Brief: plans/briefs/2026-08-06-dashboard-persistence.md
Diff reviewed: working tree (uncommitted) — `app/db/models.py`,
`tests/test_app_db.py`, new `alembic/versions/ee5ee826b050_create_dashboards_dashboard_cards.py`,
new `plans/briefs/2026-08-06-dashboard-persistence.md`

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review

```
app/db/models.py     |  25 ++++
tests/test_app_db.py | 226 ++++++++++++++++++++++++++++++++++++++++++++++++++-
2 files changed, 249 insertions(+), 2 deletions(-)
```
Plus one new migration file (~70 lines) and one new brief file. Fully
read line by line. HANDOFF.md / plans/logs/_auto-capture.md show as
modified in `git status` but are leftover uncommitted state from the
prior slice's own capture/handoff step (predates this slice's work) —
not part of this diff.

## 2. The stated goal matches the actual change

Brief's Goal: stand up the `app` schema's dashboard persistence
foundation — migration creating `dashboards`/`dashboard_cards`, ORM
models, one seeded "Overview" row — proven by a real round-trip.

The diff does exactly that: new migration `ee5ee826b050` (chained off
`f2f458dd2525`) creates both tables under `schema="app"` and seeds the
one `Overview` row; `app/db/models.py` gains `Dashboard` and
`DashboardCard` matching the migration's columns exactly; six new tests
in `tests/test_app_db.py` prove the seed, the round-trip, the FK
constraint, and cleanup. No mismatch either direction — confirmed via
`git diff --stat -- app prompts web/package.json` being empty (no
endpoint, no frontend, no other backend module touched).

## 3. The eval or test passed

```
$ .venv/Scripts/alembic upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
(exit code 0)

$ .venv/Scripts/python -m unittest discover -s tests -p "test_app_db.py" -v
test_conversation_model_has_exactly_the_briefs_columns ... ok
test_engine_authenticates_as_postgres_user ... ok
test_message_model_has_exactly_the_briefs_columns ... ok
test_cleanup_deletes_rows_leaving_no_trace_for_repeat_runs ... ok
test_content_json_round_trips_arbitrary_nested_json ... ok
test_insert_then_read_back_in_a_fresh_session_matches_values ... ok
test_message_with_nonexistent_conversation_id_violates_fk_constraint ... ok
test_cleanup_deletes_dashboard_card_leaving_no_trace_for_repeat_runs ... ok
test_dashboard_card_with_nonexistent_dashboard_id_violates_fk_constraint ... ok
test_insert_then_read_back_dashboard_card_in_a_fresh_session_matches_values ... ok
test_overview_dashboard_seed_exists_exactly_once ... ok
test_dashboard_card_model_has_exactly_the_briefs_columns ... ok
test_dashboard_model_has_exactly_the_briefs_columns ... ok

Ran 13 tests in 4.712s

OK
```
No LLM behavior changed this slice — eval run not applicable.

## 4. The no-slop review found no unresolved issues

no-slop-reviewer subagent dispatched against the diff. One real finding:
the new migration's `downgrade()` docstring enumerated the `app`
schema's current tenant tables by name ("conversations/messages and
catalog_tables/catalog_columns/kb_chunks") — the same stale-enumerated-
list pattern already flagged twice on a different file and promoted into
templates/no-slop.md §6. Fixed by generalizing to "other tables already
live in it and predate this migration" so it can't go stale as more
tables land (e.g. the not-yet-briefed `queries` table). Re-verified
clean on all ten checklist categories after the fix; tests re-run
unaffected (docstring-only change).

## 5. The shipping proof is attached

Direct `asyncpg` query against the real dev Postgres, independent of the
test suite and the ORM layer:
```
app schema tables: ['catalog_columns', 'catalog_embeddings', 'catalog_tables',
  'conversations', 'dashboard_cards', 'dashboards', 'kb_chunks', 'messages']
app.dashboards rows: [{'id': 1, 'name': 'Overview', 'created_at': datetime.datetime(2026, 8, 6, 6, 21, 18, 543025, tzinfo=datetime.timezone.utc)}]
app.dashboard_cards columns:
  id               integer            NOT NULL
  dashboard_id     integer            NOT NULL
  title            text               NOT NULL
  question_text    text               NOT NULL
  sql_text         text               NOT NULL
  chart_spec_json  jsonb              NOT NULL
  position         integer            NOT NULL
  created_at       timestamp with time zone  NOT NULL
```

## Rejected or changed

- Rejected the migration's stale-tenant-list docstring (2nd recurrence
  of the no-slop §6 pattern); fixed in place before this gate record.

## Verdict

accept — all five checks green.
