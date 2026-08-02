# Handoff

Date: 2026-08-02
Slice just completed: plans/briefs/2026-08-02-llm-table-descriptions.md +
  plans/logs/2026-08-02-llm-table-descriptions.md (commit a657fd6)

## State of the work
- M1 Foundation is now fully done per PLAN.md: docker compose db up;
  Olist loaded + RO user (4e1745b); catalog sync CLI (b55ae95); LLM table
  descriptions cached (a657fd6, this slice).
- `app/catalog/sync.py` changed from a blanket `TRUNCATE` to an UPSERT on
  `table_name` (new `UNIQUE` constraint added idempotently via a `DO`
  block, since `CREATE TABLE IF NOT EXISTS` doesn't retrofit constraints
  onto an already-existing table). `ON CONFLICT` updates `row_count`/
  `ddl_summary` only — `description` is never touched on conflict, so a
  cached description survives a re-sync. `catalog_columns` is handled by
  a `DELETE FROM ... WHERE table_id = %s` scoped to that table, then
  reinsert — no cached state to protect there.
- `app/catalog/describe.py` — CLI (`python -m app.catalog.describe`): for
  each `catalog_tables` row with `description IS NULL`, builds a prompt
  from `prompts/table_description.md` (versioned, `string.Template`
  substitution) using that table's `ddl_summary` + its columns' names/
  types/PK-FK flags/sample values, calls Claude once via the `anthropic`
  SDK, validates the JSON reply with a Pydantic model (`description: str`,
  a shared `is_genuine_paragraph()` word-count validator — one retry on
  failure, covering both a live API error and a validation failure since
  the retry loop wraps the whole attempt), writes `description`, and
  commits per-table so partial progress survives a later failure. Already-
  described rows are skipped with zero LLM calls. `ANTHROPIC_MODEL`
  env var (default `claude-sonnet-5`) is confirmed to be a real, working
  model ID — verified this session with real billed API calls.
- `app/catalog/verify_describe.py` is the working done-check: all 9
  `catalog_tables` rows have a real, non-blank, ≥20-word description.
- `requirements.txt` gained `anthropic==0.120.2`, `pydantic==2.13.4`
  (both pinned to what `pip install` resolved in the project `.venv`
  this session). `.env.example` gained `ANTHROPIC_API_KEY` and
  `ANTHROPIC_MODEL=claude-sonnet-5`. The user's local `.env` has a real,
  working `ANTHROPIC_API_KEY` (gitignored, confirmed not tracked/staged/
  leaked anywhere in the repo).
- 60 tests pass (`python -m unittest discover tests`, via the project
  `.venv`) — 42 from prior slices + 18 new/changed: real end-to-end
  `describe` runs (genuine paragraphs, distinct per table, second-run
  no-op, sync-preserves-description), `verify_describe`'s done-check
  behavior (including a forced-NULL negative case), and structural checks
  on `requirements.txt`/`.env.example`/`prompts/table_description.md`.
- `evals/table_description.md` — first eval in the project (this is the
  first LLM-driven behavior). 9/9 real cases pass a 4-point rubric
  (correct row meaning, correct PK/FK relationships including the one
  table with none, table-specific not generic, genuine paragraph) against
  `claude-sonnet-5`'s actual 2026-08-02 output.
- Gate 2 accepted: artifacts/reviews/2026-08-02-llm-table-descriptions.md.
  No-slop review caught and fixed 2 real issues before merge (retry loop
  didn't cover live API failures; prompt file re-read from disk on every
  call) plus a bug caught mid-build, not at review: a new test hand-set a
  description without restoring it in a `finally`, leaking into the real
  DB and making `describe.py` wrongly skip `customers` — fixed with
  try/finally, DB row manually repaired, description regenerated for
  real.

## Proof
```
$ python -m app.catalog.verify_describe
Descriptions:
  [OK] olist.customers: description=763 chars
  [OK] olist.geolocation: description=1107 chars
  [OK] olist.order_items: description=1019 chars
  [OK] olist.order_payments: description=854 chars
  [OK] olist.order_reviews: description=899 chars
  [OK] olist.orders: description=1028 chars
  [OK] olist.product_category_name_translation: description=901 chars
  [OK] olist.products: description=948 chars
  [OK] olist.sellers: description=864 chars

verify_describe: PASSED

$ python -m app.catalog.describe   # second run, right after the first
  olist.customers: already described, skipping
  ... (8 more "skipping" lines)
Table description sync complete.
real  0m1.018s

$ python -m app.catalog.sync && python -m app.catalog.verify_describe
Catalog sync complete.
...
verify_describe: PASSED   # descriptions survived the re-sync
```
Full suite: `Ran 60 tests ... OK`.

## Open questions / known issues
- Test runner: still `unittest`, still via the project `.venv`. Carried
  over: will likely move to pytest once FastAPI test deps land in M4 —
  that slice must update `.claude/hooks/stop_verify.py`'s TEST_CMD and
  CLAUDE.md together.
- Lint/type tooling (`ruff`, `mypy`) named in CLAUDE.md's Commands still
  aren't installed in the project `.venv` — carried over, still not
  blocking since no slice has needed them for its done-check yet.
- No FK constraints exist between `olist.*` tables (unchanged) —
  `catalog_columns.is_fk` is `false` for every column; this is correct
  given the live schema. The LLM correctly noticed and stated this for
  `product_category_name_translation`'s description rather than
  hallucinating a relationship, which is a good sign for the upcoming
  SQL-generation prompt's context quality.
- `prompts/table_description.md` asks for one JSON object; `describe.py`
  tolerates a markdown code-fence-wrapped reply (`extract_json_object`)
  but was only ever exercised against Claude's actual un-fenced replies
  this session — the fence-stripping branch itself is untested (no test
  forces a fenced reply, since that would require mocking, against this
  project's real-infra convention). Not a known bug, just an untested
  branch worth knowing about.

## Next slice (the brief, written NOW while context is hot)
Goal:
For one fixed, hardcoded natural-language business question, generate a
single SQL `SELECT` statement via one Claude API call using the full
`olist` catalog as context (all 9 tables' `ddl_summary` + LLM description
+ columns), and print the raw generated SQL to stdout — the first slice
of M2's "question → SQL → validate → execute → printed answer" pipeline,
with no retrieval yet (schema context passed whole, per PLAN.md's M2
note) and no validation/execution yet (each gets its own slice next).

Constraints:
New prompt file `prompts/generate_sql.md` (versioned, never an inline
string, per ARCHITECT.md). The LLM's JSON response (`{"sql": "..."}"`)
is validated by a new Pydantic model with exactly one retry on validation
failure, matching `describe.py`'s established pattern (retry wraps the
whole attempt, including the API call itself, not just JSON parsing) — if
the retry also fails, raise loudly, no placeholder SQL. Reuse the
existing `ANTHROPIC_API_KEY`/`ANTHROPIC_MODEL` env vars and the
`anthropic`/`pydantic` dependencies already installed — no new
dependencies without asking. Schema context is built from
`app.catalog_tables`/`app.catalog_columns` (already populated and
described) via plain psycopg2, no ORM. No sqlglot parsing, no
table/column existence validation beyond a lightweight sanity check (see
Done-check), no LIMIT/statement_timeout injection, no execution against
any database — those are explicitly the next slice's scope, not this
one's. The one fixed question for this slice must be a real Olist
business question answerable from the seeded data (e.g. "What are the
top 5 product categories by number of orders?") — pick and hardcode one
concrete question so the done-check is binary; CLI argument support for
arbitrary questions is not required this slice.

Inputs:
PRD.md §9 (Key Prompts, item 2: `generate_sql.md` — full dialect-rules/
few-shot polish is directional, not mandatory, for this first cut);
ARCHITECT.md's model/Pydantic/retry/prompt-versioning/no-orchestration-
framework decisions; `app.catalog_tables`/`app.catalog_columns` (already
real data with real LLM descriptions) as the schema context source;
`app/catalog/describe.py`'s prompt-loading/retry/Pydantic pattern as the
template to follow for consistency.

Outputs:
- `prompts/generate_sql.md` — the versioned prompt template.
- A Pydantic model for the expected `{"sql": "..."}"` LLM JSON response
  shape.
- A new module/CLI (exact path/name proposed at Gate 1, e.g.
  `app/pipeline/generate_sql.py`, runnable as
  `python -m app.pipeline.generate_sql`) that builds the full schema
  context, calls the LLM once for the one fixed question, validates via
  Pydantic (one retry), and prints the raw generated SQL string to
  stdout.
- A done-check script/test verifying the printed SQL starts with `SELECT`
  (case-insensitive) and every table/column name it references exists in
  `app.catalog_tables`/`app.catalog_columns` — a lightweight sanity check,
  not full sqlglot validation.

Done-check:
Running the new CLI against the one fixed question exits 0 and prints a
single SQL string; a verify script/test parses that output and confirms
it starts with `SELECT` and references only real `olist.*` table/column
names present in the catalog (checked against a live introspection of
`app.catalog_tables`/`app.catalog_columns`, never a hardcoded list).

Out-of-scope:
sqlglot parsing/validation, LIMIT/statement_timeout injection, actually
executing the generated SQL against any database (the read-only asyncpg
pool doesn't exist yet), the business glossary (F5/M3), retrieval/
pgvector (M3), the `analyze.md` chart/explanation step, the repair loop,
FastAPI, frontend, CI, arbitrary/multi-question CLI support.
