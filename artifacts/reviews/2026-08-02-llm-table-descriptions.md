# Review gate — LLM table descriptions

Date: 2026-08-02
Brief: plans/briefs/2026-08-02-llm-table-descriptions.md
Diff reviewed: working tree vs HEAD (0536c7d), pre-commit

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review
```
 .env.example                |  2 +
 app/catalog/sync.py         | 35 ++++++++++++++----
 requirements.txt            |  2 +
 tests/test_catalog_sync.py  | 58 +++++++++++++++++++++++------
 tests/test_env_example.py   | 17 +++++++++
 6 files changed, insertions/deletions as above (modified, tracked)

New files:
 app/catalog/describe.py
 app/catalog/verify_describe.py
 prompts/table_description.md
 tests/_describe_helpers.py
 tests/test_describe_cli.py
 tests/test_llm_description_setup.py
 tests/test_verify_describe_script.py
 plans/briefs/2026-08-02-llm-table-descriptions.md
```
(`plans/logs/_auto-capture.md` also shows modified — that's the
capture_commit hook's mechanical append of prior commits, pre-existing
before this slice started, not part of this slice's content.)
Reviewable: every file was read in full during build; no file exceeds a
few hundred lines and each has a single clear responsibility. PASS.

## 2. The stated goal matches the actual change
Brief's Goal: generate a one-paragraph LLM description for each of the 9
`app.catalog_tables` rows via one Claude API call each, persisted into
`description`, finishing PRD F4/M1.

What the diff does: `app/catalog/describe.py` does exactly this (skip
already-described rows, one call + one retry per NULL row, Pydantic
validation, loud failure on exhausted retry). `sync.py` was changed from
TRUNCATE to UPSERT-on-`table_name` so re-syncing never wipes a cached
description — this was a Constraint in the brief, not an unrequested
extra. `.env.example`/`requirements.txt` updated exactly for the two
pre-approved deps + the two new env vars. No unrequested scope (no
pgvector/`kb_chunks` writes, no glossary, no FastAPI/frontend touched).
PASS.

## 3. The eval or test passed
Done-check run fresh, immediately before writing this record:
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

$ python -m unittest discover tests
............................................................
----------------------------------------------------------------------
Ran 60 tests in 36.222s

OK
```
No eval set change (no prompt/pipeline change to `evals/questions.yaml`'s
scope — this is the first LLM call in the project, not a chat-pipeline
change; `evals/` doesn't exist yet, out of scope for M1). PASS.

## 4. The no-slop review found no unresolved issues
no-slop-reviewer subagent findings and resolution:
1. **Fixed** — retry loop only covered JSON/validation failures, not a
   live Anthropic API error on attempt 1 (would crash without using the
   retry). Moved the API call inside the same `try` so both failure modes
   share the one retry (`app/catalog/describe.py::call_llm_for_description`).
2. **Fixed** — `from string import Template` was a local import inside
   `build_prompt()`, inconsistent with the file's and codebase's
   top-of-file import convention. Moved to the top.
3. **Fixed** — `prompts/table_description.md` was re-read from disk on
   every LLM call (up to twice per table). Now read once at module load
   into `PROMPT_TEMPLATE`.
4. **Disclosed exception, not a defect** — the retry-exhausted "fail
   loudly" path is untested, because forcing a genuine validation failure
   would require mocking the Anthropic response, against this project's
   real-infrastructure-only test convention. Written as a docstring note
   in `tests/test_describe_cli.py`.
Categories 1/3/4/7/8/10 (dead code, duplication, naming, consistency,
scope, verified-not-claimed) reported clean, independently re-verified by
the reviewer (re-ran the suite and both CLIs itself). Re-ran everything
again after the three fixes above (see Check 3) — still green.
No unresolved findings remain. PASS.

## 5. The shipping proof is attached
Real, sequential runs against the live docker-compose Postgres and the
real Anthropic API this session (not mocked):
```
$ python -m app.catalog.describe        # first real run, 9 LLM calls
  olist.customers: described (763 chars)
  ... (8 more "described" lines)
Table description sync complete.

$ python -m app.catalog.describe        # second run
  olist.customers: already described, skipping
  ... (8 more "skipping" lines)
Table description sync complete.
real  0m1.018s        # zero LLM calls -- DB-only round trip

$ python -m app.catalog.sync             # re-sync after descriptions exist
Catalog sync complete.
$ python -m app.catalog.verify_describe  # descriptions survived
verify_describe: PASSED
```
All three done-check clauses (genuine descriptions, zero-cost second run,
sync doesn't wipe descriptions) demonstrated live, not just asserted by
tests. PASS.

## Rejected or changed
- Rejected the reviewer-agent's first cut of the retry loop (API call
  outside the try/retry scope) — required moving it inside so a
  transient network failure gets the same one retry as a validation
  failure, before this could be accepted.
- Caught and fixed a real bug during build (not at review): a test in
  `tests/test_catalog_sync.py` hand-set `customers.description` to a
  throwaway string without restoring it, which leaked into the real DB
  and caused `describe.py` to permanently skip `customers`. Fixed with a
  try/finally restoring the original value, and manually repaired the
  polluted DB row before re-running `describe.py` for real.

## Verdict
accept — all five checks green.
