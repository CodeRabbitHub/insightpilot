# Slice log — `app` schema persistence foundation

Date: 2026-08-04
Brief: plans/briefs/2026-08-04-app-schema-persistence.md

## The plan you approved
A SQLAlchemy 2.0 async engine + session factory at `app/db/session.py`
(authenticated as `POSTGRES_USER`, scoped to `app` only), ORM models at
`app/db/models.py` (`Conversation`, `Message`), and one hand-written
Alembic migration (async template, reusing `app/db/session.py`'s engine
directly rather than a second URL-building path) creating the `app`
schema plus both tables. Foundation only — no wiring into `/api/ask` or
`/api/ask/stream`, proven by a direct round-trip test against the pool.

## The diff you accepted
Commit `a120c4e` — "Add app schema SQLAlchemy async pool, Alembic
migration, ORM models". 14 files changed, 844 insertions(+): new
`app/db/__init__.py`, `app/db/models.py`, `app/db/session.py`,
`alembic.ini` + `alembic/env.py` + `alembic/versions/f2f458dd2525_...py`
(+ unmodified `alembic init -t async` scaffold: `README`,
`script.py.mako`), `tests/test_app_db.py` (new, 7 tests); modified
`requirements.txt` (+sqlalchemy, alembic), `tests/test_llm_description
_setup.py` (dependency ledger), `CLAUDE.md` (migration command); plus
`plans/briefs/` + `artifacts/reviews/` for this slice. Full gate record:
`artifacts/reviews/2026-08-04-app-schema-persistence.md`.

## The done-check output
```
$ .venv/Scripts/alembic.exe upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```
```
$ .venv/Scripts/python.exe -m unittest discover -s tests -p "test_app_db.py" -v
test_conversation_model_has_exactly_the_briefs_columns ... ok
test_engine_authenticates_as_postgres_user ... ok
test_message_model_has_exactly_the_briefs_columns ... ok
test_cleanup_deletes_rows_leaving_no_trace_for_repeat_runs ... ok
test_content_json_round_trips_arbitrary_nested_json ... ok
test_insert_then_read_back_in_a_fresh_session_matches_values ... ok
test_message_with_nonexistent_conversation_id_violates_fk_constraint ... ok

Ran 7 tests in 3.059s

OK
```
Full suite fresh (before the post-review fixes, unaffected by them):
`Ran 215 tests in 478.114s / OK` (208 prior + this slice's 7). Live
shipping proof (outside the test suite, against the real dev DB):
inserted a conversation+message, read both back in a fresh session,
listed `app` schema's tables (`catalog_columns, catalog_embeddings,
catalog_tables, conversations, kb_chunks, messages` — new tables sit
alongside the pre-existing ones undisturbed), deleted both, disposed the
engine. Full detail in the gate record.

## One thing you rejected or changed
**no-slop pre-gate** caught a real, not cosmetic, defect: the first
draft of `app/db/session.py`'s `database_url()` built the asyncpg DSN by
raw f-string interpolation of `POSTGRES_USER`/`POSTGRES_PASSWORD`
straight into the connection string. A password containing any
URL-reserved character (`@`, `:`, `/`, `%`, `#`) would silently
mis-parse — wrong host/db split, or a confusing auth failure — with no
error naming the actual problem. Untested and masked by the dev
`.env.example` password (`changeme`) having no special characters.
**Fixed:** rebuilt via `sqlalchemy.URL.create()`, which percent-encodes
automatically; verified empirically that `p@ss:w/rd#1` round-trips
through `.render_as_string(hide_password=False)` correctly encoded and
`.username`/`.password` still return the real values. Two smaller
findings from the same pass: the `NullPool` choice (required — asyncpg
connections are event-loop-bound and broke a real pool across
`unittest.IsolatedAsyncioTestCase`'s per-test event loops, confirmed
empirically via a live `InterfaceError`) had no forward-pointer note
that it needs re-evaluation once wired into a live single-loop process —
added one; and a test docstring misattributed a quote to the brief that
wasn't actually there — corrected. A second, fresh no-slop pass verified
all three resolved with nothing new introduced.

This is a new pattern (unencoded credential interpolation into a
connection string), not a repeat of anything in a prior slice's log — no
promotion action taken.

## The next smallest slice
Wire `/api/ask` and `/api/ask/stream` to actually create a conversation
(if none given) and persist a message per request through this slice's
new pool, so both endpoints are backed by real history instead of a
foundation with nothing plugged into it yet — explicitly the item every
prior brief's Out-of-scope, including this one's, has deferred to "the
following slice."
