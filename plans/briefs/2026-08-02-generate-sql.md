# Brief — Generate SQL from a fixed question

Date: 2026-08-02
Milestone: M2 Pipeline v0 in the CLI (question → SQL → validate → execute
→ printed answer — this slice covers only "question → SQL", no retrieval,
no validation, no execution)

Goal:
For one fixed, hardcoded natural-language business question ("What are
the top 5 product categories by number of orders?"), generate a single
SQL `SELECT` statement via one Claude API call using the full `olist`
catalog (all 9 tables' `ddl_summary` + description + columns) as schema
context, and print the raw generated SQL to stdout.

Constraints:
No new dependencies — reuse `anthropic`, `pydantic`, `python-dotenv`,
`psycopg2` already installed. One strong Claude-Sonnet-class model per
ARCHITECT.md, via the existing `ANTHROPIC_API_KEY`/`ANTHROPIC_MODEL` env
vars (already in `.env`/`.env.example`, no changes needed there). The
prompt lives in a new versioned file, `prompts/generate_sql.md` — never an
inline string (ARCHITECT.md prompt-versioning rule); full dialect-rules/
few-shot polish (PRD §9 item 2) is directional, not mandatory, for this
first cut, but the prompt must instruct the model to return exactly one
`SELECT` statement referencing only `olist.*` tables. The LLM's JSON
response (`{"sql": "..."}`) is validated by a new Pydantic model with
exactly one retry on validation failure — retry wraps the whole attempt
(API call + parse + validate), matching `describe.py`'s
`call_llm_for_description` pattern exactly; if the retry also fails,
raise loudly, no placeholder SQL. Schema context is built from
`app.catalog_tables`/`app.catalog_columns` via plain psycopg2 (reusing
`app/catalog/sync.py`'s `connect()`), no ORM. No sqlglot parsing, no
table/column existence validation beyond the done-check's lightweight
sanity check, no LIMIT/statement_timeout injection, no execution against
any database — all explicitly out-of-scope (next slices' jobs). Exact
module path: `app/pipeline/generate_sql.py`, runnable as
`python -m app.pipeline.generate_sql`; if a different path turns out to
fit the codebase better, propose the change at Gate 1 rather than
deciding silently mid-build.

Inputs:
PRD.md §9 (Key Prompts, item 2: `generate_sql.md`); ARCHITECT.md's
model/Pydantic/retry/prompt-versioning/no-orchestration-framework
decisions; `app.catalog_tables`/`app.catalog_columns` (already populated,
every table already has an LLM description from the prior slice) as the
schema context source; `app/catalog/describe.py`'s prompt-loading/retry/
Pydantic pattern as the template to follow for consistency.

Outputs:
- `prompts/generate_sql.md` — the versioned prompt template.
- A Pydantic model for the expected `{"sql": "..."}` LLM JSON response
  shape.
- `app/pipeline/generate_sql.py` — CLI (`python -m app.pipeline.generate_sql`):
  builds the full schema context from the catalog, calls the LLM once for
  the one fixed question, validates the response via Pydantic (one
  retry), prints the raw generated SQL string to stdout.
- `app/pipeline/verify_generate_sql.py` — the done-check script: runs
  `generate_sql`, then checks the returned SQL starts with `SELECT`
  (case-insensitive) and that every `olist.<table>` / bare column-name
  token it references exists in a live introspection of
  `app.catalog_tables`/`app.catalog_columns` (never a hardcoded list).

Done-check:
`python -m app.pipeline.verify_generate_sql` exits 0 only if: the fixed
question produces a printed SQL string starting with `SELECT`
(case-insensitive), and every table/column name it references is
confirmed present in `app.catalog_tables`/`app.catalog_columns` via a
live DB query at verify time.

Out-of-scope:
sqlglot parsing/validation, LIMIT/statement_timeout injection, executing
the generated SQL against any database (the read-only asyncpg pool
doesn't exist yet), the business glossary (F5/M3), retrieval/pgvector
(M3), the `analyze.md` chart/explanation step, the repair loop, FastAPI,
frontend, CI, arbitrary/multi-question CLI support (only the one fixed
question this slice).
