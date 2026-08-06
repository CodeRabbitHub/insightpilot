# Review gate — dashboard-fresh-on-view-get

Date: 2026-08-06
Brief: plans/briefs/2026-08-06-dashboard-fresh-on-view-get.md
Diff reviewed: working tree diff on `main` (app/main.py +63/-1,
tests/test_api_dashboard_cards.py +435, new
plans/briefs/2026-08-06-dashboard-fresh-on-view-get.md)

A practical gate has five checks. All five pass or nothing merges.

## 1. The diff is small enough to review
`git diff --stat -- app/main.py tests/test_api_dashboard_cards.py`: 2 files
changed, 497 insertions, 1 deletion. Fully read line by line (both the
`app/main.py` route/model diff and the four new test classes in
`tests/test_api_dashboard_cards.py`). PASS.

## 2. The stated goal matches the actual change
Brief's Goal: add `GET /api/dashboards/{id}` returning the dashboard's own
fields plus its pinned cards ordered by `position`, each card carrying
fresh `rows` from re-validating/re-executing its persisted `sql_text` on
every call (`chart_spec_json` unchanged); 404 on an unknown dashboard id;
502 (whole-request) if any card's SQL now fails validation/execution.

Diff adds exactly: the `_validate_and_execute` import,
`DashboardCardWithRows`/`DashboardDetail` Pydantic models, and the
`get_dashboard` route implementing that behavior — reusing
`app/pipeline/answer.py`'s `_validate_and_execute` directly, no
`repair_sql()` call, no LLM call, no new pool. `POST
/api/dashboards/{id}/cards` untouched. No frontend changes, no
`PATCH`/`DELETE`/`run` routes, no new dashboard-creation route — matches
Out-of-scope exactly. PASS.

## 3. The eval or test passed
No LLM behavior changed by this slice (fresh-on-view re-runs
already-generated SQL, never regenerates it), so no eval run required.
Done-check run fresh, after starting the dev Postgres container (it was
down at the start of this session — `docker compose up -d`, confirmed
healthy on port 5433):
```
$ .venv/Scripts/python -m unittest discover -s tests -p "test_api_dashboard_cards.py" -v
... (31 tests total: 12 existing POST-route tests + 19 new GET-route tests) ...
----------------------------------------------------------------------
Ran 31 tests in 6.017s

OK
```
Full new coverage: happy path with out-of-order `position` insertion
(proves ordering, not insertion order), a `rows`-matches-independent-
`execute_sql()`-call proof (proves fresh, not stale), zero-own-cards 200,
unknown-id 404, and a deliberately-broken-SQL 502 that carries no `cards`
field (proves whole-request failure, not partial dropout). PASS.

## 4. The no-slop review found no unresolved issues
`no-slop-reviewer` subagent dispatched on the finished diff. All ten
checklist categories passed clean except one judgment-level finding:

- The 404 in `get_dashboard` is raised from inside the open `async with
  session:` block — the same shape flagged as an accepted stylistic
  deviation in the prior slice (`pin-dashboard-card-endpoint`, comparing
  against `post_conversation_message`'s close-then-raise shape). Per
  HANDOFF.md's own ratchet rule ("promote if it recurs"), this is the
  second occurrence. Resolution: promoted into `templates/no-slop.md`
  (category 7) — but documented as the codebase's *dominant* shape
  (`get_conversation`, `create_dashboard_card`, and now `get_dashboard`
  all raise inside the open block; only `post_conversation_message`
  closes first, because its 404 check gates a subsequent LLM-streamed
  response rather than a same-block read). Future no-slop passes should
  no longer flag raise-inside as a deviation.

No duplication, dead-code, naming, comment, or scope findings. PASS.

## 5. The shipping proof is attached
Real `uvicorn` dev server started on port 8000 (not just the in-process
`TestClient` the tests use) and hit with real `curl` requests:
```
=== POST a real card onto Overview (dashboard 1) ===
HTTP 200: {"id":399,...,"sql_text":"select count(*) from olist.orders",...}

=== GET /api/dashboards/1 ===
HTTP 200: {"id":1,"name":"Overview",...,"cards":[{"id":399,...,"rows":[{"count":99441}]}]}

=== GET /api/dashboards/999999999 ===
HTTP 404: {"detail":"dashboard not found"}

=== POST a card with broken SQL (select * from nonexistent_table) ===
HTTP 200 (pin succeeds -- storage is opaque)

=== GET /api/dashboards/1 (now with the broken card pinned) ===
HTTP 502: {"detail":"unknown table(s) referenced: olist.nonexistent_table"}
```
Both proof cards (399, 400) deleted afterward; seeded Overview dashboard
(id 1) confirmed still present and clean (`cards: []`) via a final GET.
Server stopped. PASS.

## Rejected or changed
The no-slop finding above (check 4) was resolved by changing
`templates/no-slop.md`, not the diff itself — the code already matches
the brief's named mirror target (`get_conversation`) and the codebase's
own majority pattern, so no code change was warranted; the checklist
itself was out of date.

## Verdict
accept — all five checks green.
