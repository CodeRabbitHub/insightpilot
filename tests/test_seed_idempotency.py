"""
Integration tests for the brief's idempotency constraint: "seed idempotent,
safe to re-run" / "idempotent (safe to re-run without duplicating rows or
failing on already-applied grants)".

Runs scripts/seed.py twice as a subprocess against the real database and
compares row counts before/after. Requires: docker compose db service
running. Will fail honestly until scripts/seed.py exists.
"""
import subprocess
import sys
import unittest

from _pg_helpers import (
    REPO_ROOT,
    expected_row_counts,
    get_admin_connection,
    olist_table_row_counts,
)

SEED_SCRIPT = REPO_ROOT / "scripts" / "seed.py"
SEED_TIMEOUT_SECONDS = 900


def run_seed():
    return subprocess.run(
        [sys.executable, str(SEED_SCRIPT)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=SEED_TIMEOUT_SECONDS,
    )


class SeedIdempotencyTests(unittest.TestCase):
    def setUp(self):
        if not SEED_SCRIPT.exists():
            self.fail(f"expected seed script at {SEED_SCRIPT}")
        # touch the DB now so a connection failure surfaces as a clear
        # test failure rather than a confusing subprocess timeout
        get_admin_connection().close()

    def test_seed_runs_twice_without_error(self):
        first = run_seed()
        self.assertEqual(
            first.returncode,
            0,
            f"first seed run failed:\nstdout={first.stdout}\nstderr={first.stderr}",
        )

        second = run_seed()
        self.assertEqual(
            second.returncode,
            0,
            "re-running seed.py must not error (e.g. on already-applied "
            f"grants):\nstdout={second.stdout}\nstderr={second.stderr}",
        )

    def test_second_seed_run_does_not_duplicate_rows(self):
        run_seed()  # first run: establish a seeded baseline
        run_seed()  # second run: must not duplicate anything

        conn = get_admin_connection()
        try:
            with conn.cursor() as cur:
                actual = olist_table_row_counts(cur)
        finally:
            conn.close()

        self.assertEqual(
            actual,
            expected_row_counts(),
            "table row counts changed after re-running seed.py a second "
            "time -- rows were duplicated",
        )


if __name__ == "__main__":
    unittest.main()
