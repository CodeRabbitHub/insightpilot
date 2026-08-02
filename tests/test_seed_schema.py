"""
Integration tests for the brief's core done-check claims about the seeded
`olist` schema: the 9 tables exist, their row counts match the CSVs, and
the `vector` extension is installed.

Requires: docker compose db service running, and scripts/seed.py already
run against it. These will fail honestly until both exist.
"""
import unittest

from _pg_helpers import (
    all_csv_files,
    expected_row_counts,
    get_admin_connection,
    olist_table_names,
    olist_table_row_counts,
)


class OlistSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = get_admin_connection()
        cls.conn.autocommit = True

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "conn", None) is not None:
            cls.conn.close()

    def test_nine_csv_files_present_in_data_dir(self):
        # Sanity check on the fixture data itself, so a failure in the
        # tables-below tests can't be blamed on a missing CSV.
        self.assertEqual(
            len(all_csv_files()),
            9,
            "expected exactly 9 Olist CSVs in data/ per the brief's inputs",
        )

    def test_vector_extension_is_installed(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            row = cur.fetchone()
        self.assertIsNotNone(row, "pgvector 'vector' extension is not installed")

    def test_exactly_nine_olist_tables_exist(self):
        with self.conn.cursor() as cur:
            tables = olist_table_names(cur)
        self.assertEqual(
            len(tables),
            9,
            f"expected 9 base tables in the olist schema, found {tables}",
        )

    def test_table_row_counts_match_csv_row_counts(self):
        # No hardcoded row numbers: expected counts are read from the CSVs
        # at test time, per the brief's done-check wording.
        expected = expected_row_counts()
        with self.conn.cursor() as cur:
            actual = olist_table_row_counts(cur)
        self.assertEqual(
            actual,
            expected,
            "olist table row counts (sorted) do not match the sorted "
            "per-CSV data-row counts computed from data/*.csv",
        )


if __name__ == "__main__":
    unittest.main()
