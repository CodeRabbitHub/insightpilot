"""
The llm-table-descriptions brief's literal done-check
(plans/briefs/2026-08-02-llm-table-descriptions.md): `python -m
app.catalog.verify_describe` exits 0 only if every one of the 9
`catalog_tables` rows has a non-NULL, non-blank, genuine-paragraph
description.

Runs the exact CLI command via subprocess, mirroring
test_verify_sync_script.py's convention. Depends on a prior
`python -m app.catalog.sync` + `python -m app.catalog.describe` having
already populated descriptions -- describe.py's own "run once, cached"
behavior means calling it again here triggers zero additional LLM calls
once any prior test/run has already described all 9 tables. Will fail
honestly until app/catalog/verify_describe.py exists.
"""
import unittest

from _catalog_helpers import run_sync
from _describe_helpers import run_describe, run_verify_describe
from _pg_helpers import get_admin_connection


class VerifyDescribeDoneCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sync_result = run_sync()
        cls.describe_result = run_describe()
        cls.conn = get_admin_connection()
        cls.conn.autocommit = True

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "conn", None) is not None:
            cls.conn.close()

    def _require_described_catalog(self):
        if self.sync_result.returncode != 0:
            self.fail(
                "python -m app.catalog.sync did not exit 0:\n"
                f"stdout={self.sync_result.stdout}\nstderr={self.sync_result.stderr}"
            )
        if self.describe_result.returncode != 0:
            self.fail(
                "python -m app.catalog.describe did not exit 0, so "
                "verify_describe cannot be exercised against a fully "
                f"described catalog:\nstdout={self.describe_result.stdout}\n"
                f"stderr={self.describe_result.stderr}"
            )

    def test_verify_describe_exits_zero_against_a_described_catalog(self):
        self._require_described_catalog()

        result = run_verify_describe()
        self.assertEqual(
            result.returncode,
            0,
            "python -m app.catalog.verify_describe did not exit 0 against "
            f"a fully-described catalog (the brief's done-check):\n"
            f"stdout={result.stdout}\nstderr={result.stderr}",
        )

    def test_verify_describe_stdout_reports_a_pass_style_marker(self):
        self._require_described_catalog()

        result = run_verify_describe()
        self.assertIn(
            "PASS",
            result.stdout.upper(),
            "expected a PASS-style marker in verify_describe stdout, "
            f"matching the verify_sync.py convention:\nstdout={result.stdout}",
        )

    def test_verify_describe_fails_when_a_description_is_missing(self):
        # Behavioral proof the done-check actually validates every row,
        # not just an always-pass script: force one description back to
        # NULL and confirm verify_describe catches it, then restore the
        # original value immediately so no other test (or a future test
        # run) sees a NULL and re-triggers a real LLM call for that table.
        self._require_described_catalog()

        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, description FROM app.catalog_tables "
                "ORDER BY table_name LIMIT 1"
            )
            table_id, original_description = cur.fetchone()

        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "UPDATE app.catalog_tables SET description = NULL WHERE id = %s",
                    (table_id,),
                )

            result = run_verify_describe()
            self.assertNotEqual(
                result.returncode,
                0,
                "python -m app.catalog.verify_describe unexpectedly exited "
                "0 with one catalog_tables.description reset to NULL -- "
                "the done-check must actually validate every row:\n"
                f"stdout={result.stdout}",
            )
        finally:
            with self.conn.cursor() as cur:
                cur.execute(
                    "UPDATE app.catalog_tables SET description = %s WHERE id = %s",
                    (original_description, table_id),
                )


if __name__ == "__main__":
    unittest.main()
