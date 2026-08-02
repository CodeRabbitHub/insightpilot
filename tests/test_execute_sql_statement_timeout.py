"""
Real-DB integration test for the execute-sql brief's statement_timeout
constraint (plans/briefs/2026-08-02-execute-sql.md): "Set statement_timeout
to 10s scoped to just this query (e.g. SET LOCAL statement_timeout inside
an explicit transaction) ... this is ARCHITECT.md's defense-in-depth layer
3 (LIMIT + timeout)". A query that runs longer than 10s must be cancelled
by Postgres, not left to run indefinitely.

This is a genuinely slow test (the query must run past the 10s timeout
before Postgres cancels it) -- deliberately not skipped or shortened,
since a shorter sleep wouldn't actually prove the 10s bound is enforced
rather than some other, looser value.

Uses stdlib's unittest.IsolatedAsyncioTestCase, per the brief's explicit
note that this needs no new *test* dependency (asyncpg itself is the new
*application* dependency this brief adds).

Requires: docker compose db service running, and the olist schema /
olist_ro role already seeded. Will fail honestly (ImportError) until
app/pipeline/execute_sql.py's execute_sql() exists.
"""
import unittest

import asyncpg

from app.pipeline.execute_sql import execute_sql


class ExecuteSqlStatementTimeoutTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_query_running_longer_than_ten_seconds_is_cancelled(self):
        # pg_sleep(11) is a valid, single SELECT statement -- it clears
        # validate_sql's checks conceptually (no table/column references
        # to hallucinate) and clears cap_limit (a LIMIT is simply added),
        # so it exercises the real statement_timeout enforcement rather
        # than being rejected earlier in the pipeline for an unrelated
        # reason.
        with self.assertRaises(asyncpg.exceptions.QueryCanceledError):
            await execute_sql("SELECT pg_sleep(11)")


if __name__ == "__main__":
    unittest.main()
