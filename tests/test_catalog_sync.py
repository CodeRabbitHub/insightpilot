"""
Integration tests for the catalog-sync-cli brief
(plans/briefs/2026-08-02-catalog-sync-cli.md): `python -m app.catalog.sync`
introspects the seeded `olist` schema and persists it into
`app.catalog_tables` / `app.catalog_columns` matching PRD.md §7's exact
column shapes.

Requires: docker compose db service running, `olist` schema already
seeded (prior slice). Will fail honestly until app/catalog/sync.py
(and the app/catalog package) exist.
"""
import json
import os
import subprocess
import sys
import unittest

import psycopg2.sql as sql

from _catalog_helpers import (
    live_distinct_sample_values,
    live_foreign_key_columns,
    live_primary_key_columns,
    olist_columns,
    pick_representative_columns,
    run_sync,
)
from _pg_helpers import REPO_ROOT, get_admin_connection, olist_table_names


def _parse_sample_values(raw):
    if raw is None:
        return None
    if isinstance(raw, str):
        return json.loads(raw)
    return raw


class CatalogSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sync_result = run_sync()
        cls.conn = get_admin_connection()
        cls.conn.autocommit = True

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "conn", None) is not None:
            cls.conn.close()

    def setUp(self):
        if self.sync_result.returncode != 0:
            self.fail(
                "python -m app.catalog.sync did not exit 0, so the catalog "
                "tables under test do not exist:\n"
                f"stdout={self.sync_result.stdout}\nstderr={self.sync_result.stderr}"
            )

    def test_catalog_tables_has_exactly_nine_rows(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM app.catalog_tables")
            count = cur.fetchone()[0]
        self.assertEqual(
            count, 9, "expected exactly one catalog_tables row per olist table"
        )

    def test_catalog_tables_row_count_matches_live_olist_counts(self):
        with self.conn.cursor() as cur:
            tables = olist_table_names(cur)
            self.assertEqual(len(tables), 9, f"expected 9 olist tables, found {tables}")
            for table_name in tables:
                cur.execute(
                    sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
                        sql.Identifier("olist"), sql.Identifier(table_name)
                    )
                )
                live_count = cur.fetchone()[0]
                cur.execute(
                    "SELECT row_count FROM app.catalog_tables WHERE table_name = %s",
                    (table_name,),
                )
                row = cur.fetchone()
                self.assertIsNotNone(row, f"no catalog_tables row for olist.{table_name}")
                self.assertEqual(
                    row[0],
                    live_count,
                    f"catalog_tables.row_count for {table_name} does not match "
                    "a live SELECT COUNT(*)",
                )

    def test_catalog_tables_ddl_summary_non_empty(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT table_name, ddl_summary FROM app.catalog_tables")
            rows = cur.fetchall()
        self.assertEqual(len(rows), 9)
        for table_name, ddl_summary in rows:
            self.assertIsNotNone(ddl_summary, f"ddl_summary is NULL for {table_name}")
            self.assertTrue(
                ddl_summary.strip(), f"ddl_summary is blank for {table_name}"
            )

    def test_catalog_tables_description_is_null_for_all_rows(self):
        # Out-of-scope guard: LLM-generated descriptions are a later slice
        # per the brief -- no LLM calls should have happened this slice.
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM app.catalog_tables WHERE description IS NOT NULL"
            )
            rows = cur.fetchall()
        self.assertEqual(
            rows,
            [],
            "catalog_tables.description should stay NULL this slice, found "
            f"non-null for: {rows}",
        )

    def test_catalog_columns_names_match_information_schema_per_table(self):
        with self.conn.cursor() as cur:
            tables = olist_table_names(cur)
            for table_name in tables:
                live_cols = {name for name, _ in olist_columns(cur, table_name)}
                cur.execute(
                    "SELECT cc.column_name FROM app.catalog_columns cc "
                    "JOIN app.catalog_tables ct ON cc.table_id = ct.id "
                    "WHERE ct.table_name = %s",
                    (table_name,),
                )
                catalog_cols = {row[0] for row in cur.fetchall()}
                self.assertEqual(
                    catalog_cols,
                    live_cols,
                    f"catalog_columns column set for {table_name} does not "
                    "match information_schema.columns",
                )

    def test_catalog_columns_total_row_count_matches_information_schema(self):
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = 'olist'"
            )
            live_total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM app.catalog_columns")
            catalog_total = cur.fetchone()[0]
        self.assertEqual(
            catalog_total,
            live_total,
            "app.catalog_columns row count does not match the total olist "
            "column count from information_schema",
        )

    def test_is_pk_matches_live_primary_keys_no_false_positives_or_negatives(self):
        with self.conn.cursor() as cur:
            live_pks = live_primary_key_columns(cur)
            cur.execute(
                "SELECT ct.table_name, cc.column_name, cc.is_pk "
                "FROM app.catalog_columns cc "
                "JOIN app.catalog_tables ct ON cc.table_id = ct.id"
            )
            rows = cur.fetchall()
        self.assertTrue(rows, "app.catalog_columns is empty")
        for table_name, column_name, is_pk in rows:
            expected = (table_name, column_name) in live_pks
            self.assertEqual(
                is_pk,
                expected,
                f"is_pk mismatch for {table_name}.{column_name}: expected "
                f"{expected} (live PK introspection), got {is_pk}",
            )

    def test_is_fk_and_ref_table_match_live_foreign_keys(self):
        with self.conn.cursor() as cur:
            live_fks = live_foreign_key_columns(cur)
            cur.execute(
                "SELECT ct.table_name, cc.column_name, cc.is_fk, cc.ref_table "
                "FROM app.catalog_columns cc "
                "JOIN app.catalog_tables ct ON cc.table_id = ct.id"
            )
            rows = cur.fetchall()
        self.assertTrue(rows, "app.catalog_columns is empty")
        for table_name, column_name, is_fk, ref_table in rows:
            key = (table_name, column_name)
            if key in live_fks:
                self.assertTrue(
                    is_fk, f"is_fk should be true for {table_name}.{column_name}"
                )
                self.assertEqual(
                    ref_table,
                    live_fks[key],
                    f"ref_table mismatch for {table_name}.{column_name}",
                )
            else:
                self.assertFalse(
                    is_fk,
                    f"is_fk should be false for {table_name}.{column_name} "
                    "(no live FK constraint exists)",
                )
                self.assertIsNone(
                    ref_table,
                    f"ref_table should be NULL for non-FK column "
                    f"{table_name}.{column_name}",
                )

    def test_sample_values_are_distinct_ascending_non_null_for_representative_columns(self):
        with self.conn.cursor() as cur:
            picked = pick_representative_columns(cur)
        self.assertTrue(
            picked,
            "could not find any representative text/numeric/timestamp "
            "columns in olist via information_schema",
        )
        for category, (table_name, column_name) in picked.items():
            with self.subTest(category=category, table=table_name, column=column_name):
                with self.conn.cursor() as cur:
                    expected = live_distinct_sample_values(cur, table_name, column_name)
                    cur.execute(
                        "SELECT cc.sample_values_json FROM app.catalog_columns cc "
                        "JOIN app.catalog_tables ct ON cc.table_id = ct.id "
                        "WHERE ct.table_name = %s AND cc.column_name = %s",
                        (table_name, column_name),
                    )
                    row = cur.fetchone()
                self.assertIsNotNone(
                    row, f"no catalog_columns row for {table_name}.{column_name}"
                )
                actual = _parse_sample_values(row[0])
                self.assertIsNotNone(
                    actual,
                    f"sample_values_json is NULL for {table_name}.{column_name}",
                )
                actual_str = [str(v) for v in actual]
                expected_str = [str(v) for v in expected]
                self.assertEqual(
                    actual_str,
                    expected_str,
                    f"sample_values_json for {table_name}.{column_name} does "
                    "not match a live 'SELECT DISTINCT ... WHERE col IS NOT "
                    "NULL ORDER BY col ASC LIMIT 5'",
                )
                self.assertEqual(
                    len(actual_str),
                    len(set(actual_str)),
                    f"sample_values_json for {table_name}.{column_name} "
                    "contains duplicate values",
                )
                self.assertLessEqual(
                    len(actual_str),
                    5,
                    f"sample_values_json for {table_name}.{column_name} has "
                    "more than 5 values",
                )

    def test_sync_is_idempotent_row_counts_stable_across_two_runs(self):
        second_result = run_sync()
        self.assertEqual(
            second_result.returncode,
            0,
            "re-running python -m app.catalog.sync must not error:\n"
            f"stdout={second_result.stdout}\nstderr={second_result.stderr}",
        )

        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM app.catalog_tables")
            tables_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM app.catalog_columns")
            columns_count = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = 'olist'"
            )
            live_total = cur.fetchone()[0]

        self.assertEqual(
            tables_count,
            9,
            "catalog_tables row count changed after a second sync run "
            "(expected truncate + reinsert, not accumulation)",
        )
        self.assertEqual(
            columns_count,
            live_total,
            "catalog_columns row count changed after a second sync run "
            "(expected truncate + reinsert, not accumulation)",
        )

    def test_olist_ro_lacks_create_privilege_on_app_schema(self):
        # The brief requires sync to connect as POSTGRES_USER (owner),
        # never olist_ro. This checks the read-only role could not itself
        # have created the app schema / catalog tables -- i.e. sync
        # attempted as olist_ro would necessarily fail.
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT has_schema_privilege(%s, 'app', 'CREATE')",
                (os.environ["OLIST_RO_USER"],),
            )
            has_create = cur.fetchone()[0]
        self.assertFalse(
            has_create,
            "olist_ro unexpectedly has CREATE privilege on the app schema "
            "-- sync must never be reachable via the read-only role",
        )

    def test_sync_run_as_olist_ro_actually_fails(self):
        # Behavioral proof, not just a privilege-table check: running the
        # real CLI with the RO role's credentials must itself error out,
        # matching scripts/verify_seed.py's check_ro_permissions convention
        # of proving the restriction by attempting the forbidden action.
        env = dict(os.environ)
        env["POSTGRES_USER"] = os.environ["OLIST_RO_USER"]
        env["POSTGRES_PASSWORD"] = os.environ["OLIST_RO_PASSWORD"]
        result = subprocess.run(
            [sys.executable, "-m", "app.catalog.sync"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertNotEqual(
            result.returncode,
            0,
            "python -m app.catalog.sync unexpectedly succeeded when run "
            f"with olist_ro credentials:\nstdout={result.stdout}",
        )
        self.assertIn(
            "InsufficientPrivilege",
            result.stderr,
            "expected a permission-denied failure when sync is run as "
            f"olist_ro, got:\nstderr={result.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
