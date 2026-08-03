# Handoff

Date: 2026-08-03
Slice just completed: plans/briefs/2026-08-02-eval-harness-v1.md +
  plans/logs/2026-08-03-eval-harness-v1.md (commit cd1edf0, plus a
  follow-up ratchet commit 3e92b00 to CLAUDE.md)

## State of the work
- **The project has its first automated accuracy number.** `evals/run.py`
  loads `evals/questions.yaml` (5 curated questions, each hand-verified
  live against the real `olist` DB this session), runs each through the
  real `answer.get_answer(question)` pipeline, grades pass/fail via
  `check_expected()` (two assertion kinds: `top_row` — membership check
  against the first result row's values, column-order/name agnostic;
  `scalar` — single-value match with an optional `tolerance`), and prints
  a per-question PASS/FAIL line plus an "N/5 correct" summary. Current
  real score: 5/5.
- `app/pipeline/generate_sql.py`'s `generate_sql()` and
  `app/pipeline/answer.py`'s `get_answer()` both gained an optional
  `question` parameter (default `FIXED_QUESTION`) — every existing
  zero-arg CLI/verify script call site is unchanged and still passes.
- `requirements.txt` gained `PyYAML==6.0.3` (pinned, confirmed at Gate 1).
- `evals/__init__.py` (empty) + `evals/questions.yaml` (a top-level YAML
  list — not a `{questions: [...]}` wrapper — of 5
  `{question, expected}` mappings) + `evals/run.py` (`load_questions`,
  `check_expected`, `format_summary`, `main`) are new. This exact shape
  came from the test-writer subagent (blind to my own Gate-1 plan, which
  had proposed a wrapper dict and a different function contract) — the
  tests were treated as the real spec once written, and the
  implementation was built to match them.
- New tests: `tests/test_eval_questions_yaml.py` (structural checks on
  the yaml), `tests/test_eval_run_grading.py` (pure, no-network unit
  tests for `check_expected`/`load_questions`/`format_summary` against
  synthetic fixtures — the brief's "known-good and known-bad fixture
  case" requirement), `tests/test_eval_run_cli.py` +
  `tests/_eval_helpers.py` (the literal done-check, real/billed),
  `tests/test_question_parameter.py` (pure signature checks plus two
  real end-to-end classes proving the `question` param is genuine
  plumbing, not silently ignored). `tests/test_llm_description_setup.py`
  extended for the `pyyaml` dependency allowlist + a version-pin check.
- **A real, previously-undiagnosed bug in `.claude/hooks/stop_verify.py`
  was found and fixed this session**: its subprocess timeout was 300s,
  but the real suite now takes ~650-900s (real Voyage/Anthropic calls,
  Voyage's free-tier 3 RPM limit). The old timeout was silently killing
  the suite mid-run on every agent turn; a hard kill can skip a test's
  `finally` cleanup, and two *pre-existing, unrelated* tests
  (`test_catalog_sync.py`'s `test_sync_preserves_an_existing_description_across_a_resync`,
  `test_verify_describe_script.py`'s `test_verify_describe_fails_when_a_description_is_missing`)
  mutate-then-restore a shared `app.catalog_tables.customers.description`
  row as part of their own checks, so a kill mid-flight permanently
  corrupts it until someone notices and repairs it by hand (which
  happened, repeatedly, this session — always fixed via
  `UPDATE ... SET description = NULL` + `python -m app.catalog.describe`
  to regenerate a real one). Timeout bumped to 1200s (commit `cd1edf0`);
  CLAUDE.md's `Test:` line now documents the real ~15min runtime (commit
  `3e92b00`), a second-repetition ratchet promotion (Voyage rate limits
  have now caused friction in two consecutive slices).
- `evals/generate_sql.md`/`evals/table_description.md` were NOT extended
  this slice — this slice's own `evals/questions.yaml` + `evals/run.py`
  *is* the eval artifact; no prompt or retrieval logic changed, only
  which question flows through the existing pipeline.

## Proof
```
$ python -m evals.run
[PASS] What are the top 5 product categories by number of orders?
[PASS] Which payment type is used the most, by number of payments?
[PASS] Which customer state has the most customers?
[PASS] How many orders have the status 'delivered'?
[PASS] What is the average review score across all reviews?
5/5 correct

$ python -m unittest discover tests
.............................................................................................................................................
----------------------------------------------------------------------
Ran 139 tests in 651.003s

OK
```

## Open questions / known issues
- **A deeper, systemic concurrency hazard remains, unfixed.** Even after
  the stop_verify.py timeout fix, a full-suite run can still hit the same
  `customers`-description corruption if two full-suite invocations
  genuinely overlap in time (confirmed directly this session: a second
  fresh attempt during this slice's own gate hit the identical symptom
  with zero code changes in between). The Stop hook fires automatically
  on every agent turn boundary, so a long-running manual
  `python -m unittest discover tests` (this session's real runtime:
  ~650-900s) can overlap with one or more hook-triggered runs, and the
  two genuinely race on the same DB row via ordinary concurrent-access
  semantics (not just kills). Root cause is now well understood
  (two pre-existing tests do a non-atomic "capture original, mutate,
  verify, restore" against `ORDER BY table_name LIMIT 1`, i.e. always
  `customers`, with no locking), but a real fix (e.g. a stop_verify lock
  file so overlapping invocations can't run concurrently, or making
  those two tests target an isolated row/table instead of a shared one)
  was explicitly deferred as out-of-scope for this slice, by direct user
  decision. **If a future session sees `customers`'s description show up
  as `'a hand-set description for this test'` or fail a
  word-count/idempotency check, this is why** — repair via
  `UPDATE app.catalog_tables SET description = NULL WHERE table_name =
  'customers'` then `python -m app.catalog.describe`, not by touching
  test logic.
- **Voyage's free-tier 3 RPM rate limit continues to be a real,
  recurring cost** (now flagged twice — see CLAUDE.md's `Test:` line).
  Any future slice adding more Voyage calls (e.g. the glossary retrieval
  slice below) will add to the real suite's already-long runtime.
- Lint/type tooling (`ruff`, `mypy`) and the test runner (`unittest`, not
  `pytest`) remain unaddressed, carried over from every prior slice —
  still not blocking.

## Next slice (the brief, written NOW while context is hot)
Goal:
For the fixed question (and, by extension, every `evals/questions.yaml`
question), `generate_sql()`'s prompt context includes top-k relevant
business-glossary entries (KPI definitions) alongside the existing top-k
schema context, retrieved via the same pgvector pattern already built
for schema retrieval.

Constraints:
New file `glossary.md` at the repo root, seeded with ~15 KPI definitions
per PRD.md F5 (Revenue, AOV, Repeat purchase rate, Delivery time, Review
score, Churn proxy, etc.), each with an exact formula referencing real
`olist` columns — hand-written/verified against the real schema, not
invented loosely. Reuse the exact same Voyage AI embeddings provider,
`voyage-3.5` model, and `embed_text()`'s existing rate-limit
retry-with-backoff (`app/catalog/embed.py`) — no new provider, no
reinvented retry logic. New `app`-schema table for glossary chunk
embeddings (one row per KPI definition; exact name proposed at Gate 1 —
`app.kb_chunks` was explicitly reserved as out-of-scope-to-create by the
llm-table-descriptions slice's own tests, strongly implying it's the
intended name here). New idempotent embed script mirroring
`app/catalog/embed.py`'s exact convention (skip already-embedded
entries, commit per-row, its own `verify_*` CLI). `generate_sql.py` gains
a `retrieve_relevant_glossary_entries(cur, voyage_client, question, k=...)`
analogous to the existing `retrieve_relevant_tables()`, called with the
same `question` parameter now threaded through `generate_sql()`.
`prompts/generate_sql.md` gains a glossary-context placeholder (a real
templated section, not a hardcoded string). Per CLAUDE.md's binding
rule, a prompt change without an eval run is not done — `evals/run.py`
must be re-run after this change and its score reported, even if
unchanged from 5/5. No new dependencies expected (reuses `voyageai`,
already pinned).

Inputs:
PRD.md's F5 section (glossary spec: ~15 KPIs, chunked per definition,
embedded into pgvector, retrieved alongside schema context); ARCHITECT.md
(Voyage AI + pgvector decisions); `app/catalog/embed.py` (the exact
pattern to mirror: `SCHEMA_DDL`, `to_vector_literal`, `embed_text`,
idempotent `embed()`); `app/pipeline/generate_sql.py`'s
`retrieve_relevant_tables()`/`build_schema_context()`/`build_prompt()`/
`generate_sql()`; `prompts/generate_sql.md`; `evals/questions.yaml` +
`evals/run.py` (this slice's own eval harness, used to prove glossary
retrieval doesn't regress accuracy).

Outputs:
- `glossary.md` — ~15 KPI definitions with real `olist` column
  references.
- New DDL (`app.kb_chunks` or the name confirmed at Gate 1): one
  embedding vector + chunk text per glossary entry.
- A new idempotent embed script + its own `verify_*` CLI, mirroring
  `app/catalog/embed.py`'s convention exactly.
- `generate_sql.py` gains `retrieve_relevant_glossary_entries()` +
  glossary-context building, called alongside the existing schema
  retrieval inside `generate_sql()`, using the same `question`.
- `prompts/generate_sql.md` extended with a real glossary-context
  section.
- Tests: glossary retrieval returns a genuine top-k subset (never a
  hardcoded full-list check, mirroring the schema-retrieval slice's own
  test precedent); the new embed script is idempotent across two runs.
- `evals/run.py`'s score re-reported after the prompt change (still 5/5,
  or an honestly lower/different number with an explanation).

Done-check:
`python -m evals.run` exits 0 and reports its score after the glossary
context is added — paste output, and confirm it's not a regression from
this slice's 5/5. Separately, `python -m unittest discover tests` passes
in full — paste output (expect ~15-20 min real runtime; not hung, see
CLAUDE.md).

Out-of-scope:
Document upload/parsing UI (F5 explicitly excludes this — glossary is
seeded, not uploaded); the one-shot repair loop (a separate remaining M3
slice); changing `retrieve_relevant_tables()`/schema retrieval's own
behavior; `validate_sql.py`/`execute_sql.py` internals; FastAPI/frontend;
CI; fixing the deeper stop_verify.py/shared-DB-test concurrency hazard
noted above (a real, separate, dedicated slice of its own).
