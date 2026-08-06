# Brief — dashboard persistence foundation

Date: 2026-08-06
Milestone: M6 Dashboard (first slice — schema/models foundation only;
  "Pin" endpoint/UI and the card grid are later slices, mirroring M4's
  `app-schema-persistence` precedent of migration+models before wiring)

Goal:
Stand up the `app` schema's dashboard persistence foundation — an
Alembic migration creating `dashboards` and `dashboard_cards` tables
(PRD.md §7), their SQLAlchemy ORM models, and a seeded single default
"Overview" dashboard row — proven by a real round-trip (insert a card,
read it back) against the dev Postgres instance.

Constraints:
- Reuse the existing SQLAlchemy async engine/session in
  `app/db/session.py` (the `POSTGRES_USER`-authenticated, app-schema-only
  read-write pool already used by `Conversation`/`Message`) — no new
  pool, no new dependency.
- Scope to exactly two tables from PRD.md §7: `dashboards` (id, name,
  created_at) and `dashboard_cards` (id, dashboard_id FK, title,
  question_text, sql_text, chart_spec_json, position, created_at).
- `dashboard_id` is a non-nullable FK to `app.dashboards.id` (mirrors
  `messages.conversation_id`'s FK pattern). `chart_spec_json` is JSONB,
  non-nullable (mirrors `messages.content_json` — a pinned card always
  has a resolved chart spec at pin time). `position` is a non-nullable
  Integer with no server default — the (not-yet-built) pin endpoint sets
  it explicitly, same as `messages.role` today.
- The migration seeds exactly one row into `dashboards`: `name="Overview"`
  (PRD F6: "One default dashboard").
- No new API endpoint and no frontend change this slice — schema/models
  only, proven by a direct test against the pool, not through HTTP. This
  mirrors the `app-schema-persistence` slice's own precedent (migration +
  models first, endpoint wiring is a separate following slice).
- Real round-trip test against the real dev Postgres (no mocking),
  matching this project's established convention
  (`tests/test_app_db.py`'s existing `Conversation`/`Message` tests).

Inputs:
- PRD.md §7 (`dashboards`/`dashboard_cards` columns) and §6 F6 ("One
  default dashboard").
- `app/db/models.py` — `Conversation`/`Message` as the ORM model pattern
  to extend (same file, same `Base`).
- `alembic/versions/f2f458dd2525_create_app_schema_conversations_messages.py`
  — the migration pattern to mirror: `op.create_table(..., schema="app")`,
  FK via `sa.ForeignKey("app.<table>.id")`, and a follow-up `op.execute`
  for the seed insert.
- `tests/test_app_db.py` — the existing round-trip test pattern
  (insert through the ORM, read back, assert, delete in `finally`) to
  extend or mirror for `dashboard_cards`.

Outputs:
- New Alembic migration: creates `dashboards` + `dashboard_cards` tables
  under the `app` schema, and seeds the one "Overview" `dashboards` row.
- `app/db/models.py` gains `Dashboard` and `DashboardCard` SQLAlchemy 2.0
  declarative ORM models matching the migration.
- `tests/test_app_db.py` gains a round-trip test: look up the seeded
  Overview dashboard by name, insert a `DashboardCard` under it, read it
  back in a fresh session, assert the values (title, question_text,
  sql_text, chart_spec_json, position) match, then delete it in a
  `finally` block (never delete the seeded Overview row itself).

Done-check:
Both, pasted, fresh, in one sitting:
1. `alembic upgrade head` exits 0 against the real dev Postgres instance.
2. `python -m unittest discover -s tests -p "test_app_db.py" -v` passing.

Out-of-scope:
- Any new API endpoint (`POST /api/dashboards/{id}/cards`,
  `GET /api/dashboards/{id}`, `PATCH /api/cards/{id}`) — next slice.
- Any frontend "Pin" button, dashboard page, or card grid — later slice.
- `catalog_tables`/`catalog_columns`/`kb_chunks` (already exist,
  untouched).
- `users` table and any auth (F8, separate milestone).
- `queries` table (PRD §7's fourth `app`-schema table — a separate,
  not-yet-briefed slice).
