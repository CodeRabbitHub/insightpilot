"""
Real-DB integration tests proving app.pipeline.execute_sql.execute_sql()
genuinely runs through the OLIST_RO_USER role (plans/briefs/2026-08-02-
execute-sql.md's Constraints: the asyncpg connection MUST authenticate as
OLIST_RO_USER/OLIST_RO_PASSWORD, never POSTGRES_USER/POSTGRES_PASSWORD --
blast-radius isolation via the read-only grant is the product's core
safety property).

Two things are proven here, deliberately kept separate:

  1. execute_sql() itself, called for real (no mocking), against the real
     database, for a trivial SELECT -- returns real rows. This exercises
     the actual public coroutine under test.
  2. The exact OLIST_RO_USER/OLIST_RO_PASSWORD credentials that
     execute_sql() is required to use are denied a write against a real,
     dynamically-fetched olist table (never a hardcoded table name, per
     tests/test_olist_ro_permissions.py's pattern) -- proving those
     credentials, not just execute_sql()'s own code, are the read-only
     backstop. This is checked via a raw asyncpg connection opened
     directly with the same credentials rather than by forcing
     execute_sql() itself to accept a non-SELECT statement, since
     execute_sql()'s LIMIT-injection step (cap_limit) only ever expects a
     SELECT -- validating/rejecting non-SELECT SQL is validate_sql.py's
     job (out of scope for this slice, per the brief), not execute_sql()'s.

Uses stdlib's unittest.IsolatedAsyncioTestCase, per the brief's explicit
note that this needs no new *test* dependency. It does require the new
*application* dependency `asyncpg` (which this brief adds to
requirements.txt) to actually be installed.

Requires: docker compose db service running, and the olist schema /
olist_ro role already seeded (make seed / scripts/seed.py). These will
fail honestly until app/pipeline/execute_sql.py's execute_sql() exists
and asyncpg is installed.
"""
import os
import unittest

import asyncpg

from _pg_helpers import get_admin_connection, olist_table_names

from app.pipeline.execute_sql import execute_sql


def _ro_asyncpg_kwargs():
    return {
        "host": os.environ["POSTGRES_HOST"],
        "port": int(os.environ["POSTGRES_PORT"]),
        "database": os.environ["POSTGRES_DB"],
        "user": os.environ["OLIST_RO_USER"],
        "password": os.environ["OLIST_RO_PASSWORD"],
    }


def _row_value(row, key, index=0):
    """Tolerate whatever row shape execute_sql() returns (asyncpg.Record,
    a dict, or a plain tuple/list) -- the brief only promises "returns the
    result rows", not one specific row type."""
    try:
        return row[key]
    except (TypeError, KeyError, IndexError):
        return row[index]


class ExecuteSqlReadOnlyRoleTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        admin_conn = get_admin_connection()
        try:
            with admin_conn.cursor() as cur:
                tables = olist_table_names(cur)
        finally:
            admin_conn.close()
        if not tables:
            raise RuntimeError(
                "no tables found in the olist schema; seed the database "
                "before running these tests"
            )
        cls.sample_table = tables[0]

    async def test_execute_sql_returns_real_rows_for_a_trivial_select(self):
        rows = await execute_sql("SELECT 1 AS answer")
        self.assertGreaterEqual(
            len(rows),
            1,
            f"expected at least one row back from a trivial SELECT, got: {rows!r}",
        )
        value = _row_value(rows[0], "answer")
        self.assertEqual(
            value,
            1,
            "expected the trivial SELECT's real result to be 1, got: "
            f"{value!r} (full rows: {rows!r})",
        )

    async def test_a_write_through_the_same_ro_credentials_is_denied(self):
        conn = await asyncpg.connect(**_ro_asyncpg_kwargs())
        try:
            with self.assertRaises(asyncpg.exceptions.InsufficientPrivilegeError):
                await conn.execute(
                    f'INSERT INTO olist."{self.sample_table}" DEFAULT VALUES'
                )
        finally:
            await conn.close()


if __name__ == "__main__":
    unittest.main()
