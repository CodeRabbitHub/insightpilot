"""
The catalog-sync-cli brief's literal done-check
(plans/briefs/2026-08-02-catalog-sync-cli.md): `python -m
app.catalog.verify_sync` exits 0 only if app.catalog_tables /
app.catalog_columns fully match a live introspection of the seeded
`olist` schema.

Runs the exact CLI command via subprocess and checks the exit code and a
PASS-style stdout marker, mirroring test_verify_seed_script.py's
convention for scripts/verify_seed.py. Will fail honestly until
app/catalog/sync.py and app/catalog/verify_sync.py exist.
"""
import unittest

from _catalog_helpers import run_sync, run_verify_sync


class VerifySyncDoneCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Establish a correctly-synced catalog first, matching the brief's
        # scenario: verify_sync run "against a correctly-synced catalog".
        cls.sync_result = run_sync()

    def _require_synced_catalog(self):
        if self.sync_result.returncode != 0:
            self.fail(
                "python -m app.catalog.sync did not exit 0, so "
                "verify_sync cannot be exercised against a synced "
                f"catalog:\nstdout={self.sync_result.stdout}\n"
                f"stderr={self.sync_result.stderr}"
            )

    def test_verify_sync_exits_zero_against_a_synced_catalog(self):
        self._require_synced_catalog()

        result = run_verify_sync()
        self.assertEqual(
            result.returncode,
            0,
            "python -m app.catalog.verify_sync did not exit 0 against a "
            f"correctly-synced catalog (the brief's done-check):\n"
            f"stdout={result.stdout}\nstderr={result.stderr}",
        )

    def test_verify_sync_stdout_reports_a_pass_style_marker(self):
        self._require_synced_catalog()

        result = run_verify_sync()
        self.assertIn(
            "PASS",
            result.stdout.upper(),
            "expected a PASS-style marker in verify_sync stdout, matching "
            f"the verify_seed.py convention:\nstdout={result.stdout}",
        )


if __name__ == "__main__":
    unittest.main()
