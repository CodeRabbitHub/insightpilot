# Handoff

Date: 2026-08-02
Slice just completed: plans/briefs/2026-08-02-catalog-sync-cli.md +
  plans/logs/2026-08-02-catalog-sync-cli.md (commit b55ae95, capture e71e2a2)

## State of the work
- Repo git-initialized (main branch); Phase 0 scaffold (95a20c2),
  Foundation DB + seed (4e1745b), stop_verify venv fix (dbc77f1), Catalog
  sync CLI (b55ae95) all committed.
- `app/__init__.py` and `app/catalog/__init__.py` exist — first code under
  the `app/` package (the future FastAPI backend lands here from M4 on).
- `app/catalog/sync.py` — CLI (`python -m app.catalog.sync`): connects as
  `POSTGRES_USER` (never `OLIST_RO_USER`), creates `app` schema +
  `catalog_tables(id, table_name, description, row_count, ddl_summary)` /
  `catalog_columns(id, table_id, column_name, data_type, is_pk, is_fk,
  ref_table, sample_values_json)` if absent, then on every run TRUNCATEs
  and reinserts both tables from a live introspection of `olist` via
  `information_schema`/`pg_catalog` (no hardcoded table list). Per table:
  real row count, a reconstructed CREATE-TABLE-style `ddl_summary` (the
  only place nullability is recorded), real PK/FK flags, and up to 5
  distinct ascending non-null sample values per column. `description` is
  always NULL — no LLM calls this slice.
- `app/catalog/verify_sync.py` is the working done-check: table-row
  counts, per-table `ddl_summary` non-empty, per-table column-name sets,
  PK/FK correctness (both directions), sample-value correctness — all
  checked against a live `information_schema` introspection, never a
  hardcoded expectation.
- 42 tests pass (`python -m unittest discover tests`, via the project
  `.venv`) — 28 from the foundation slice + 14 new: table/column/PK/FK/
  sample-value correctness, idempotency (2 runs, stable counts), and a
  **behavioral** proof that running sync under `OLIST_RO_USER` credentials
  fails with `InsufficientPrivilege` (not just a privilege-table check).
- No new dependencies this slice (`requirements.txt` unchanged:
  `psycopg2-binary`, `python-dotenv`).
- `templates/no-slop.md` gained a new "Untested edges" line: claimed
  restrictions/failure paths must be proven by actually triggering them,
  not by checking a config/grant/state proxy — promoted after the 2nd
  occurrence (foundation slice's untested KeyError fix; this slice's
  original `has_schema_privilege`-only RO test).
- Gate 2 accepted: artifacts/reviews/2026-08-02-catalog-sync-cli.md.

## Proof
```
$ python -m app.catalog.sync
  olist.customers: 5 columns, 99441 rows
  olist.geolocation: 5 columns, 1000163 rows
  olist.order_items: 7 columns, 112650 rows
  olist.order_payments: 5 columns, 103886 rows
  olist.order_reviews: 7 columns, 99224 rows
  olist.orders: 8 columns, 99441 rows
  olist.product_category_name_translation: 2 columns, 71 rows
  olist.products: 9 columns, 32951 rows
  olist.sellers: 4 columns, 3095 rows
Catalog sync complete.

$ python -m app.catalog.verify_sync
Table rows:
  [OK] app.catalog_tables: 9 rows (expected 9)
  [OK] olist.customers: row_count=99441 (expected 99441), ddl_summary=set
  ... (all 9 OK)
Columns:
  [OK] ... (all 9 OK)
Primary keys:
  [OK] primary keys match live introspection
Foreign keys:
  [OK] foreign keys match live introspection
Sample values:
  [OK] sample values match live introspection

verify_sync: PASSED
```
Full suite: `Ran 42 tests ... OK`.

## Open questions / known issues
- Test runner: still `unittest`, still run via the project `.venv`
  (`.claude/hooks/stop_verify.py` was fixed in dbc77f1 to use it instead
  of the harness's own venv). Carried over: project will likely move to
  pytest once FastAPI test deps land in M4 — that slice must update
  `stop_verify.py` TEST_CMD and CLAUDE.md together.
- **`sync.py`'s TRUNCATE will wipe cached LLM descriptions on a re-run.**
  The next slice adds `catalog_tables.description` via one LLM call per
  table, "run once, cached" per PRD F4 — but `sync.py` currently
  TRUNCATEs + reinserts `catalog_tables` from scratch (`description`
  always NULL) on every single run, with no awareness that a description
  might already exist. If `python -m app.catalog.sync` is ever re-run
  after descriptions are generated, they're gone. The next slice's plan
  must explicitly decide how to resolve this (e.g. change `sync.py` to
  UPSERT on `table_name` and preserve existing `description` values
  instead of truncating) — flagged here so it isn't discovered by
  surprise mid-implementation.
- No FK constraints exist between `olist.*` tables (carried over,
  unchanged) — `catalog_columns.is_fk` is `false` for every column today;
  this is correct given the live schema, not a bug in the sync.
- Lint/type tooling (`ruff`, `mypy`) named in CLAUDE.md's Commands aren't
  installed in the project `.venv` yet (`requirements.txt` only has
  `psycopg2-binary`, `python-dotenv`) — carried over, not yet blocking
  since no slice has needed them for its done-check.

## Next slice (the brief, written NOW while context is hot)
Goal:
For each of the 9 rows in `app.catalog_tables`, generate a one-paragraph
natural-language description via a single Claude API call and persist it
into `catalog_tables.description`, finishing PRD F4 / M1.

Constraints:
New dependencies, pre-approved by the user for this slice: `anthropic`
(the official SDK, for the API call) and `pydantic` (for validating the
LLM's JSON output) — add both to `requirements.txt`. One strong
Claude-Sonnet-class model per ARCHITECT.md; API key via a new
`ANTHROPIC_API_KEY` env var (add to `.env.example`), model name
env-configurable. The prompt lives in a new versioned file,
`prompts/table_description.md` — never an inline string. The LLM's JSON
response is validated by a Pydantic model with exactly one retry on
validation failure; if the retry also fails for a table, the run must
fail loudly (raise / non-zero exit) for that table — no silent skip, no
placeholder text pretending to be a real description. "Run once, cached"
(PRD F4): skip any table whose `description` is already non-NULL — never
re-call the LLM for an already-described table. This slice's plan MUST
explicitly resolve the open question above (`sync.py`'s TRUNCATE wiping
cached descriptions on re-run) before implementation — likely by changing
`sync.py` to UPSERT `catalog_tables` on `table_name` instead of
truncating, preserving `description` across re-syncs; propose this at
Gate 1, don't decide it silently mid-build. No embeddings/pgvector writes
(`kb_chunks` stays untouched, M3 scope). Plain psycopg2 for all DB access,
no ORM, consistent with the existing stack.

Inputs:
PRD.md §4 (F4) and §9 (Key Prompts, for prompt-file conventions);
ARCHITECT.md's model/Pydantic/retry/prompt-versioning decisions;
`app/catalog/sync.py`'s existing `catalog_tables`/`catalog_columns` data
(`ddl_summary`, column names/types/sample values) as the context fed to
the LLM per table; the working `ANTHROPIC_API_KEY` the user will provide
locally in `.env` (gitignored).

Outputs:
- `prompts/table_description.md` — the versioned prompt template.
- `app/catalog/describe.py` — the CLI (`python -m app.catalog.describe`):
  for each `catalog_tables` row with `description IS NULL`, builds
  context from that table's `ddl_summary` and its columns/sample values,
  calls the LLM once, validates the response via Pydantic (one retry),
  writes `description`.
- A Pydantic model for the expected LLM JSON response shape (e.g. in
  `app/catalog/describe.py` or a small new `app/catalog/models.py`).
- `app/catalog/verify_describe.py` — the done-check script.
- `sync.py` changed to UPSERT-preserve `description` across re-syncs (per
  the Constraints resolution above) — exact mechanism decided at Gate 1.
- `.env.example` gains `ANTHROPIC_API_KEY` (+ model-name var if made
  configurable); `requirements.txt` gains `anthropic`, `pydantic`.

Done-check:
`python -m app.catalog.verify_describe` exits 0 only if: every one of the
9 `catalog_tables` rows has a non-NULL, non-blank `description` that
reads as a genuine paragraph (not a stub); running
`python -m app.catalog.describe` a second time makes zero additional LLM
calls (all 9 tables already described) and still exits 0; running
`python -m app.catalog.sync` after descriptions exist does NOT reset
`description` back to NULL.

Out-of-scope:
Embeddings/pgvector writes to `kb_chunks` (M3), the business glossary
(F5), any change to `olist` schema tables or the shape of
`catalog_columns`, FastAPI, frontend, CI, the chat/SQL-generation
pipeline (M2).
