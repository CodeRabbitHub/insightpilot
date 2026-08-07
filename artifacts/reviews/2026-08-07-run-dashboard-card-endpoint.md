# Review gate — run-dashboard-card-endpoint

Date: 2026-08-07
Brief: plans/briefs/2026-08-07-run-dashboard-card-endpoint.md
Diff reviewed: working tree diff (uncommitted) — `app/main.py`,
`tests/test_api_dashboard_cards.py`

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review

```
app/main.py                       |  31 +++
plans/logs/_auto-capture.md       | 497 ++++++++++++++++++++++++++++++++++++++
tests/test_api_dashboard_cards.py | 260 ++++++++++++++++++++
3 files changed, 788 insertions(+)
```
`app/main.py` (+31, one new route) and `tests/test_api_dashboard_cards.py`
(+260, 12 new test methods across 3 classes) were read line by line.
`plans/logs/_auto-capture.md` is the automated commit-capture log (hook-
appended, not authored content) — not part of the reviewable diff.
**PASS.**

## 2. The stated goal matches the actual change

Brief's Goal: add `POST /api/cards/{card_id}/run` that re-validates and
re-executes exactly one existing card's stored `sql_text` and returns its
fresh rows, without touching the rest of its dashboard.

The diff adds exactly `run_dashboard_card` in `app/main.py`: existence
check → 404 `{"detail": "card not found"}` → close the app session →
`_validate_and_execute(sql_text)` → 502 with `detail` on failure → build
`DashboardCardWithRows` from the pre-fetched snapshot + fresh rows. No
request body/query params accepted. No new Pydantic model, no new pool.
`create_dashboard_card`, `get_dashboard`, `patch_dashboard_card`,
`delete_dashboard_card` are byte-for-byte untouched. No unrequested
extras. **PASS.**

## 3. The eval or test passed

Done-check, run fresh:
```
.venv/Scripts/python -m unittest discover -s tests -p "test_api_dashboard_cards.py" -v
...
Ran 76 tests in 48.282s

OK
```
**PASS.**

## 4. The no-slop review found no unresolved issues

`no-slop-reviewer` subagent walked all 10 categories. One finding:

- **[Duplication]** `app/main.py`'s new route is the **4th** copy-paste
  occurrence of the same 7-field ORM→`DashboardCardDetail` mapping
  (previously in `create_dashboard_card`, `get_dashboard`'s per-card
  loop, `patch_dashboard_card`). The checklist's own rule is "third
  occurrence → extract."

  **Resolution: written exception, not fixed.** Extracting a shared
  helper would require editing the three existing call sites, and the
  approved brief explicitly binds those three routes as untouched this
  slice ("Existing `POST /api/dashboards/{id}/cards`, `GET
  /api/dashboards/{id}`, `PATCH /api/cards/{id}`... are untouched").
  Fixing it here would smuggle an unrequested refactor into a slice
  scoped to one new route. Flagged for the ratchet rule (2nd repetition
  → promote; this is the 4th) — the next slice that touches any of these
  four routes should extract `_card_to_detail(card) ->
  DashboardCardDetail` across all of them.

All other 9 categories checked clean (dead code, error handling, naming,
untested edges, comments, consistency, scope, fake-done, verified-not-
claimed). **PASS** (one finding, resolved via written exception).

## 5. The shipping proof is attached

Real running `uvicorn` dev server (pre-existing process on :8000, backed
by the real Postgres dev DB) hit with real `curl` — not `TestClient`:

```
=== POST a real proof card onto Overview (dashboard 1) ===
{"id":1568,"dashboard_id":1,"title":"Run-proof card","question_text":"how many rows","sql_text":"select 1 as n, 2 as m","chart_spec_json":{"type":"bar"},"position":99,"created_at":"2026-08-07T08:16:27.742057Z"}

=== POST /run on it ===
{"id":1568,"dashboard_id":1,"title":"Run-proof card","question_text":"how many rows","sql_text":"select 1 as n, 2 as m","chart_spec_json":{"type":"bar"},"position":99,"created_at":"2026-08-07T08:16:27.742057Z","rows":[{"n":1,"m":2}]}
HTTP 200

=== POST /run on an unknown id ===
{"detail":"card not found"}
HTTP 404

=== clean up the proof card ===
HTTP 204

=== proof: bad sql_text -> 502 ===
{"id":1569,"dashboard_id":1,"title":"Bad SQL run-proof card",...}
POST /api/cards/1569/run:
{"detail":"unknown table(s) referenced: olist.table_that_does_not_exist"}
HTTP 502

=== clean up ===
HTTP 204
```
Both proof cards deleted afterward; no leftover rows from this gate.
**PASS.**

## Rejected or changed

Rejected extracting a shared `_card_to_detail` helper to resolve the
no-slop duplication finding, despite it being the checklist's flagged
4th-repetition case — because doing so would have meant editing the three
existing routes the approved brief explicitly scoped as untouched.
Carried as a written exception instead, with an explicit pointer for the
next slice that touches this surface to do the extraction.

## Verdict

accept — all five checks green.
