# Review gate — card-to-detail-refactor

Date: 2026-08-07
Brief: plans/briefs/2026-08-07-card-to-detail-refactor.md
Diff reviewed: working tree diff of `app/main.py` (pre-commit)

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review

```
$ git diff --stat -- app/main.py
 app/main.py | 58 +++++++++++++++++-----------------------------------------
 1 file changed, 17 insertions(+), 41 deletions(-)
```

17 lines added, 41 removed, one file. Read in full. PASS.

## 2. The stated goal matches the actual change

Brief's Goal: extract the 4x-duplicated `DashboardCard`→`DashboardCardDetail`
mapping in `app/main.py` into one `_card_to_detail(card)` helper and use it
at all four call sites, with zero behavior change.

The diff adds exactly one private module-level function,
`_card_to_detail(card: DashboardCard) -> DashboardCardDetail`, placed
immediately above `_persist_exchange` (matching the file's existing
leading-underscore private-helper convention), and replaces all four
inline constructions:
- `create_dashboard_card` → `result = _card_to_detail(card)`
- `patch_dashboard_card` → `result = _card_to_detail(card)`
- `run_dashboard_card` → `card_detail = _card_to_detail(card)` (its
  existing `DashboardCardWithRows(**card_detail.model_dump(), rows=rows)`
  line is untouched — it already used the pattern being generalized)
- `get_dashboard` → its own separate 8-field `DashboardCardWithRows(...)`
  construction is replaced with
  `DashboardCardWithRows(**_card_to_detail(card).model_dump(), rows=rows)`,
  adopting `run_dashboard_card`'s precedent as the brief specified.

No route's status code, field set, field values, or field ordering
changed. No new endpoint, model, or dependency. Nothing outside these four
sites was touched. PASS — no missing behavior, no unrequested extras.

## 3. The eval or test passed

Brief's done-check, run fresh:

```
$ .venv/Scripts/python -m unittest discover -s tests -p "test_api_dashboard_cards.py" -v
...
Ran 76 tests in 33.290s

OK
```

76 tests, 0 failures — matches the pre-refactor count exactly. PASS.

## 4. The no-slop review found no unresolved issues

Dispatched the no-slop-reviewer subagent against `git diff -- app/main.py`.
Verdict: no findings in any of the 10 categories against `app/main.py`.
Specifically confirmed: the extraction is complete at all 4 sites with no
old inline block left anywhere in the file (category 3); `_card_to_detail`
follows the existing `_persist_exchange`-style naming (category 4); session-
boundary structure is unchanged in both `run_dashboard_card` and
`get_dashboard` (category 7); nothing touched beyond the four named routes
(category 8); the done-check was verified fresh by the reviewer itself,
independently reproducing the same 76/0 result (category 10).

The reviewer separately flagged, as pre-existing working-tree state
unrelated to this diff: `HANDOFF.md` and `plans/logs/_auto-capture.md`
modified, and an untracked `plans/logs/2026-08-07-run-dashboard-card-
endpoint.md` — all present in `git status` before this slice's work began
(confirmed against the session's starting gitStatus snapshot), none
touching behavior, and the orphaned log's cause (a skipped capture-commit
for the prior `run-dashboard-card-endpoint` slice) predates this refactor.
No action taken on them in this slice — flagged for the next handoff
instead of silently absorbed into this diff's scope. No unresolved finding
in `app/main.py`. PASS.

## 5. The shipping proof is attached

Real dev server (`uvicorn`, already running on port 8000, confirmed
serving via `GET /api/dashboards/1` → 200 before starting), real Postgres —
exercised all four refactored routes end-to-end:

```
=== POST /api/dashboards/1/cards (create_dashboard_card) ===
{"id":2292,"dashboard_id":1,"title":"Gate-check proof: refactor",
 "question_text":"How many orders per state?","sql_text":"SELECT
 customer_state, COUNT(*) AS n FROM olist.orders o JOIN olist.customers c
 ON c.customer_id = o.customer_id GROUP BY customer_state ORDER BY n DESC
 LIMIT 3","chart_spec_json":{"type":"bar"},"position":99,
 "created_at":"2026-08-07T11:44:05.126407Z"}

=== PATCH /api/cards/2292 (patch_dashboard_card) ===
{"id":2292,"dashboard_id":1,"title":"Gate-check proof: refactor (patched)",
 ...same 8 fields, title updated, everything else unchanged...}

=== POST /api/cards/2292/run (run_dashboard_card) ===
{"id":2292,"dashboard_id":1,"title":"Gate-check proof: refactor (patched)",
 ...same 8 fields plus...
 "rows":[{"customer_state":"SP","n":41746},
         {"customer_state":"RJ","n":12852},
         {"customer_state":"MG","n":11635}]}

=== GET /api/dashboards/1 (get_dashboard) — this card's entry ===
{"id":2292,"dashboard_id":1,"title":"Gate-check proof: refactor (patched)",
 ...identical 8 fields plus "rows" with the same 3 real aggregate rows...}

=== DELETE /api/cards/2292 ===
status: 204

=== POST /api/cards/2292/run again (post-delete) ===
{"detail":"card not found"}
```

All four routes returned the expected 8-field shape (9 with `rows` for
`run`/`get_dashboard`), sourced from a real SQL aggregate query
(customer-order counts by state), matching the pre-refactor field set
exactly. Proof card (id 2292) deleted afterward — zero DB pollution left
by this slice. PASS.

## Rejected or changed

Nothing was rejected mid-slice — the plan executed exactly as approved at
Gate 1, and the implementation matched the brief on the first pass (no
build-loop retries needed). If forced to name one thing: I chose to skip
spawning the test-writer subagent for this slice (deviating from the
loop's default step 4), since the brief's Out-of-scope explicitly states
no test-behavior change is needed beyond keeping the existing suite green,
and the existing 76 tests already assert exact response shapes on all
four touched routes — a subagent given the brief would have had nothing
new to derive. This was a deliberate call at Gate 1's plan-approval stage,
not a retroactive excuse.

## Verdict

**accept** — all five checks green.
