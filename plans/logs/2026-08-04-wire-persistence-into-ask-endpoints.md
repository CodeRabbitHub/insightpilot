# Slice log — wire persistence into /api/ask endpoints

Date: 2026-08-04
Brief: plans/briefs/2026-08-04-wire-persistence-into-ask-endpoints.md

## The plan you approved
Add one `_persist_exchange(question, response)` helper in `app/main.py`
that opens a session via the existing `async_session_factory`, creates a
`Conversation`, flushes for its id, adds a `user` `Message` (the question)
and an `assistant` `Message` (`jsonable_encoder(response)` — the same
shape already returned to the client), and commits. Called once from
`/api/ask` after building `AskResponse` (never inside the `try/except`
around `get_answer()`), and once from `_ask_stream_events` after building
the SSE `result` payload (the `error` branch returns earlier, so it never
runs). No new pool, no model/migration change, no response-contract change.

## The diff you accepted
Commit `60c0baf` — "Wire /api/ask and /api/ask/stream to persist
conversations/messages." `app/main.py` +36/-1; `HANDOFF.md` +13 (documents
the accepted stream-truncation-on-persist-failure gap); new
`tests/test_api_ask_persistence.py` (506 lines, 14 tests, test-writer
subagent from the brief alone); new
`plans/briefs/2026-08-04-wire-persistence-into-ask-endpoints.md`. Gate
record: `artifacts/reviews/2026-08-04-wire-persistence-into-ask-endpoints.md`
(verdict: accept, all five checks green).

## The done-check output
```
$ .venv/Scripts/python.exe -m unittest discover -s tests -p "test_api_ask*.py" -v
[... 32 tests, all roles/setUpClass/mocking conventions preserved ...]
----------------------------------------------------------------------
Ran 32 tests in 50.614s

OK
```
Full suite, no regressions: `Ran 229 tests in 545.926s / OK` (215 prior +
14 new).

## One thing you rejected or changed
Rejected the original plan's test-identification strategy at Gate 1
**before any test code was written**: snapshotting `max(conversations.id)`
before the HTTP call and asserting an exact diff of "one new row" silently
assumes no concurrent writer to `app.conversations` — false here, since
the stop_verify hook can run this same suite concurrently with a manual
run against the real dev DB, and this is a code-change slice so the hook
still fires. Replaced with: happy-path checks look up the single newest
conversation (`ORDER BY id DESC LIMIT 1`) instead of diffing a count;
failure-path checks use a distinctive per-test question string and assert
no message anywhere holds that exact `content_json`, instead of "no new
conversation exists at all." Folded into the brief itself (not just this
session's plan) so the test-writer subagent, which only reads the brief,
built the concurrency-safe version from the start.

Also fixed one no-slop finding at pre-gate: `test_api_ask_persistence.py`'s
closing docstring paragraph claimed "app/main.py has not been modified
yet," which the diff it shipped alongside falsifies — rewritten to
describe the file's actual history.

**Promoted:** this is the same underlying hazard as the Stop-hook/shared-
DB-row concurrency issue flagged across three prior sessions (commits
ba76f79's log, 280f7c6, c20157/dcededb/ca028de's hook fixes) — but a
different specific shape: those fixed the *hook's* firing frequency; this
is about **test assertion design** against shared real-DB tables. Per
direct sign-off, added a new templates/no-slop.md line under category 5:
a test asserting against a shared/real-DB table the hook can write to
concurrently must scope its check to the newest row it created (or a
value distinctive to that test run), never snapshot-then-diff or
global-count assertions.

## The next smallest slice
Replace the interim `/api/ask` / `/api/ask/stream` endpoints with PRD.md
§8's real API surface (e.g. `POST /api/conversations`,
`POST /api/conversations/{id}/messages`) so `conversation_id`/`message_id`
are finally returned to the client and multi-turn continuation becomes
possible — the natural continuation of this slice's persistence work,
chosen over starting M5's frontend scaffold or fixing the
stream-truncation-on-persist-failure gap.
