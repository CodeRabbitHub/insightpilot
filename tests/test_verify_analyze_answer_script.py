"""
The analyze_answer pipeline step's literal done-check
(plans/briefs/2026-08-05-analyze-answer.md): `python -m
app.pipeline.verify_analyze_answer` exits 0, having called the real
get_answer() (from app.pipeline.answer) for the real FIXED_QUESTION (from
app.pipeline.generate_sql) to get a real (sql, rows) pair -- not
hand-faked input -- then passed it to a real analyze_answer() call,
asserting the result satisfies AnalyzeResponse with non-empty
summary/explanation/follow_ups and a chart_spec dict.

Requires: docker compose db service running, the catalog already synced
and described (prior slices), and working ANTHROPIC_API_KEY/
VOYAGE_API_KEY values in .env -- it makes REAL, billed calls: two Voyage
embed calls plus two Anthropic calls (generate_sql, then analyze_answer),
chained through get_answer() and analyze_answer(). The subprocess is
invoked exactly once, cached in setUpClass, and shared across every test
method in this class -- never once per test method -- since each
invocation is a real, billed multi-call chain.

Will fail honestly until app/pipeline/verify_analyze_answer.py (and the
app/pipeline/analyze_answer.py module it depends on) exist.
"""
import unittest

from _analyze_answer_helpers import run_verify_analyze_answer
from _catalog_helpers import run_sync
from _describe_helpers import run_describe


class VerifyAnalyzeAnswerDoneCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sync_result = run_sync()
        cls.describe_result = run_describe()
        cls.verify_result = None
        if cls.sync_result.returncode == 0 and cls.describe_result.returncode == 0:
            cls.verify_result = run_verify_analyze_answer()

    def setUp(self):
        if self.sync_result.returncode != 0:
            self.fail(
                "python -m app.catalog.sync did not exit 0:\n"
                f"stdout={self.sync_result.stdout}\nstderr={self.sync_result.stderr}"
            )
        if self.describe_result.returncode != 0:
            self.fail(
                "python -m app.catalog.describe did not exit 0, so "
                "verify_analyze_answer cannot be exercised against a "
                f"fully-described catalog:\nstdout={self.describe_result.stdout}\n"
                f"stderr={self.describe_result.stderr}"
            )

    def test_verify_analyze_answer_exits_zero_for_the_fixed_question(self):
        self.assertEqual(
            self.verify_result.returncode,
            0,
            "python -m app.pipeline.verify_analyze_answer did not exit 0 "
            "for the fixed question (the brief's done-check):\n"
            f"stdout={self.verify_result.stdout}\nstderr={self.verify_result.stderr}",
        )

    def test_verify_analyze_answer_stdout_reports_the_passed_marker(self):
        self.assertIn(
            "verify_analyze_answer: PASSED",
            self.verify_result.stdout,
            "expected the exact 'verify_analyze_answer: PASSED' marker in "
            "stdout (matching verify_answer.py/verify_generate_sql.py's "
            f"`<script>: PASSED` convention):\nstdout={self.verify_result.stdout}",
        )


if __name__ == "__main__":
    unittest.main()
