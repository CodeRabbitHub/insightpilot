"""
The brief's literal done-check: `python scripts/verify_seed.py` exits 0
only if all 9 olist tables exist with row counts matching the CSVs, the
vector extension is installed, and INSERT as olist_ro raises a permissions
error.

This test just runs that exact command and checks the exit code, so it
stands in one-to-one for the done-check itself. Will fail honestly until
scripts/verify_seed.py exists and the database is seeded.
"""
import subprocess
import sys
import unittest

from _pg_helpers import REPO_ROOT

VERIFY_SCRIPT = REPO_ROOT / "scripts" / "verify_seed.py"
VERIFY_TIMEOUT_SECONDS = 120


class VerifySeedDoneCheckTests(unittest.TestCase):
    def test_verify_seed_exits_zero(self):
        if not VERIFY_SCRIPT.exists():
            self.fail(f"expected verify script at {VERIFY_SCRIPT}")

        result = subprocess.run(
            [sys.executable, str(VERIFY_SCRIPT)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT_SECONDS,
        )

        self.assertEqual(
            result.returncode,
            0,
            "scripts/verify_seed.py did not exit 0 (the brief's done-check):"
            f"\nstdout={result.stdout}\nstderr={result.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
