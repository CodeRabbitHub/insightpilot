"""
The execute-sql brief's literal done-check
(plans/briefs/2026-08-02-execute-sql.md): `python -m
app.pipeline.verify_answer` exits 0 and prints the fixed question's real
result rows, having chained generate_sql() -> validate_sql() ->
execute_sql() end to end and executed the final, validated SQL only
through a read-only asyncpg connection authenticated as OLIST_RO_USER.

Requires: docker compose db service running, the catalog already synced
and described (prior slices), and a working ANTHROPIC_API_KEY in .env --
it makes a REAL, billed call to the Anthropic API via generate_sql() (no
"already done" cache exists for this slice), plus a real query executed
against the live database via the new asyncpg connection.

Will fail honestly until app/pipeline/verify_answer.py (and the
app/pipeline/answer.py and app/pipeline/execute_sql.py modules it
depends on) exist.
"""
import unittest

from _answer_helpers import run_verify_answer
from _catalog_helpers import run_sync
from _describe_helpers import run_describe


class VerifyAnswerDoneCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sync_result = run_sync()
        cls.describe_result = run_describe()

    def _require_described_catalog(self):
        if self.sync_result.returncode != 0:
            self.fail(
                "python -m app.catalog.sync did not exit 0:\n"
                f"stdout={self.sync_result.stdout}\nstderr={self.sync_result.stderr}"
            )
        if self.describe_result.returncode != 0:
            self.fail(
                "python -m app.catalog.describe did not exit 0, so "
                "verify_answer cannot be exercised against a fully-described "
                f"catalog:\nstdout={self.describe_result.stdout}\n"
                f"stderr={self.describe_result.stderr}"
            )

    def test_verify_answer_exits_zero_for_the_fixed_question(self):
        self._require_described_catalog()

        result = run_verify_answer()
        self.assertEqual(
            result.returncode,
            0,
            "python -m app.pipeline.verify_answer did not exit 0 for the "
            f"fixed question (the brief's done-check):\n"
            f"stdout={result.stdout}\nstderr={result.stderr}",
        )

    def test_verify_answer_stdout_reports_the_passed_marker(self):
        self._require_described_catalog()

        result = run_verify_answer()
        self.assertIn(
            "verify_answer: PASSED",
            result.stdout,
            "expected the exact 'verify_answer: PASSED' marker in stdout "
            "(matching verify_generate_sql.py/verify_sync.py/"
            f"verify_describe.py's `<script>: PASSED` convention):\n"
            f"stdout={result.stdout}",
        )

    def test_verify_answer_stdout_includes_the_real_result_rows(self):
        self._require_described_catalog()

        result = run_verify_answer()
        self.assertEqual(
            result.returncode,
            0,
            "expected exit 0 before checking for printed result rows:\n"
            f"stdout={result.stdout}\nstderr={result.stderr}",
        )
        non_blank_lines = [
            line for line in result.stdout.splitlines() if line.strip()
        ]
        self.assertGreater(
            len(non_blank_lines),
            1,
            "expected verify_answer's stdout to include the fixed "
            "question's real, executed result rows in addition to the "
            f"PASSED marker line, got only:\n{result.stdout!r}",
        )


if __name__ == "__main__":
    unittest.main()
