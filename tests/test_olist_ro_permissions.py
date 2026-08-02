"""
Integration tests for the brief's read-only-role safety property:
`olist_ro` must be able to SELECT, and must have zero DDL/DML grants
beyond that -- not just fail on INSERT, but on UPDATE/DELETE/CREATE TABLE
too (per the brief's Constraints: "olist_ro gets zero DDL/DML grants
beyond SELECT").

Requires: docker compose db service running, and scripts/seed.py already
run against it (creates the olist schema + olist_ro role). These will
fail honestly until both exist.
"""
import unittest

import psycopg2
import psycopg2.errors
import psycopg2.sql as sql

from _pg_helpers import get_admin_connection, get_ro_connection, olist_table_names


class OlistRoPermissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin_conn = get_admin_connection()
        cls.admin_conn.autocommit = True
        with cls.admin_conn.cursor() as cur:
            tables = olist_table_names(cur)
        if not tables:
            raise RuntimeError(
                "no tables found in the olist schema; seed the database "
                "before running these tests"
            )
        cls.sample_table = tables[0]
        with cls.admin_conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = %s "
                "ORDER BY ordinal_position LIMIT 1",
                ("olist", cls.sample_table),
            )
            cls.sample_column = cur.fetchone()[0]

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "admin_conn", None) is not None:
            cls.admin_conn.close()

    def setUp(self):
        self.ro_conn = get_ro_connection()

    def tearDown(self):
        self.ro_conn.close()

    def test_ro_user_can_select(self):
        with self.ro_conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT * FROM {}.{} LIMIT 1").format(
                    sql.Identifier("olist"), sql.Identifier(self.sample_table)
                )
            )
            cur.fetchall()  # must not raise

    def test_ro_insert_denied(self):
        with self.ro_conn.cursor() as cur:
            with self.assertRaises(psycopg2.errors.InsufficientPrivilege):
                cur.execute(
                    sql.SQL("INSERT INTO {}.{} DEFAULT VALUES").format(
                        sql.Identifier("olist"), sql.Identifier(self.sample_table)
                    )
                )
        self.ro_conn.rollback()

    def test_ro_update_denied(self):
        with self.ro_conn.cursor() as cur:
            with self.assertRaises(psycopg2.errors.InsufficientPrivilege):
                cur.execute(
                    sql.SQL("UPDATE {}.{} SET {} = {} WHERE 1 = 0").format(
                        sql.Identifier("olist"),
                        sql.Identifier(self.sample_table),
                        sql.Identifier(self.sample_column),
                        sql.Identifier(self.sample_column),
                    )
                )
        self.ro_conn.rollback()

    def test_ro_delete_denied(self):
        with self.ro_conn.cursor() as cur:
            with self.assertRaises(psycopg2.errors.InsufficientPrivilege):
                cur.execute(
                    sql.SQL("DELETE FROM {}.{} WHERE 1 = 0").format(
                        sql.Identifier("olist"), sql.Identifier(self.sample_table)
                    )
                )
        self.ro_conn.rollback()

    def test_ro_create_table_denied(self):
        with self.ro_conn.cursor() as cur:
            with self.assertRaises(psycopg2.errors.InsufficientPrivilege):
                cur.execute(
                    "CREATE TABLE olist.__ro_permission_probe (id int)"
                )
        self.ro_conn.rollback()

    def test_ro_has_select_privilege_on_every_olist_table(self):
        with self.admin_conn.cursor() as cur:
            tables = olist_table_names(cur)
            for table in tables:
                cur.execute(
                    "SELECT has_table_privilege(%s, %s, 'SELECT')",
                    ("olist_ro", f"olist.{table}"),
                )
                self.assertTrue(
                    cur.fetchone()[0],
                    f"olist_ro is missing SELECT privilege on olist.{table}",
                )

    def test_ro_has_no_write_privilege_on_any_olist_table(self):
        with self.admin_conn.cursor() as cur:
            tables = olist_table_names(cur)
            for table in tables:
                for privilege in ("INSERT", "UPDATE", "DELETE", "TRUNCATE"):
                    cur.execute(
                        "SELECT has_table_privilege(%s, %s, %s)",
                        ("olist_ro", f"olist.{table}", privilege),
                    )
                    self.assertFalse(
                        cur.fetchone()[0],
                        f"olist_ro unexpectedly has {privilege} on olist.{table}",
                    )

    def test_ro_has_no_create_privilege_on_olist_schema(self):
        with self.admin_conn.cursor() as cur:
            cur.execute(
                "SELECT has_schema_privilege(%s, %s, 'CREATE')",
                ("olist_ro", "olist"),
            )
            self.assertFalse(
                cur.fetchone()[0],
                "olist_ro unexpectedly has CREATE privilege on the olist schema",
            )


if __name__ == "__main__":
    unittest.main()
