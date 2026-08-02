# Brief — LLM table descriptions

Date: 2026-08-02
Milestone: M1 Foundation (docker compose up; Olist loaded; SELECT-only
user; catalog sync CLI; LLM table descriptions cached — this is the last
item)

Goal:
For each of the 9 rows in `app.catalog_tables`, generate a one-paragraph
natural-language description via a single Claude API call and persist it
into `catalog_tables.description`, finishing PRD F4 / M1.

Constraints:
New dependencies, pre-approved for this slice: `anthropic` (official SDK)
and `pydantic` (validates the LLM's JSON output) — add both to
`requirements.txt`; no other new dependencies. One strong Claude-Sonnet-
class model per ARCHITECT.md; API key via a new `ANTHROPIC_API_KEY` env
var (add to `.env.example`), model name env-configurable. The prompt lives
in a new versioned file, `prompts/table_description.md` — never an inline
string (ARCHITECT.md prompt-versioning rule). The LLM's JSON response is
validated by a Pydantic model with exactly one retry on validation
failure; if the retry also fails for a table, the run fails loudly (raise
/ non-zero exit) for that table — no silent skip, no placeholder text
pretending to be a real description. "Run once, cached" (PRD F4): skip any
table whose `description` is already non-NULL — never re-call the LLM for
an already-described table. Plain psycopg2 for all DB access, no ORM,
consistent with the existing stack. `sync.py`'s current TRUNCATE-and-
reinsert of `catalog_tables` must be changed to UPSERT on `table_name`,
preserving any existing `description` across re-syncs — resolve the exact
mechanism at Gate 1, not silently mid-build. No embeddings/pgvector writes
(`kb_chunks` stays untouched, M3 scope).

Inputs:
PRD.md §4 (F4) and §9 (Key Prompts, prompt-file conventions);
ARCHITECT.md's model/Pydantic/retry/prompt-versioning decisions;
`app/catalog/sync.py`'s existing `catalog_tables`/`catalog_columns` data
(`ddl_summary`, column names/types/sample values) as the context fed to
the LLM per table; a working `ANTHROPIC_API_KEY` the user provides locally
in `.env` (gitignored).

Outputs:
- `prompts/table_description.md` — the versioned prompt template.
- `app/catalog/describe.py` — CLI (`python -m app.catalog.describe`): for
  each `catalog_tables` row with `description IS NULL`, builds context
  from that table's `ddl_summary` and its columns/sample values, calls the
  LLM once, validates the response via Pydantic (one retry), writes
  `description`.
- A Pydantic model for the expected LLM JSON response shape.
- `app/catalog/verify_describe.py` — the done-check script.
- `sync.py` changed to UPSERT `catalog_tables` on `table_name`, preserving
  `description` across re-syncs.
- `.env.example` gains `ANTHROPIC_API_KEY` (+ model-name var);
  `requirements.txt` gains `anthropic`, `pydantic`.

Done-check:
`python -m app.catalog.verify_describe` exits 0 only if: every one of the
9 `catalog_tables` rows has a non-NULL, non-blank `description` that reads
as a genuine paragraph (not a stub); running `python -m app.catalog.describe`
a second time makes zero additional LLM calls (all 9 tables already
described) and still exits 0; running `python -m app.catalog.sync` after
descriptions exist does NOT reset `description` back to NULL.

Out-of-scope:
Embeddings/pgvector writes to `kb_chunks` (M3), the business glossary
(F5), any change to the `olist` schema tables or the shape of
`catalog_columns`, FastAPI, frontend, CI, the chat/SQL-generation pipeline
(M2).
