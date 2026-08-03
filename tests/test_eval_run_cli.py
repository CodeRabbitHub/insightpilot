"""
The eval-harness-v1 brief's literal done-check
(plans/briefs/2026-08-02-eval-harness-v1.md): `python -m evals.run` exits
0 and prints a real accuracy score (e.g. "N/N correct" or honestly fewer)
for the curated questions in `evals/questions.yaml` (5 originally; the
glossary-retrieval slice added a 6th, and this set is expected to keep
growing per templates/eval.md's "every production/demo failure adds a
case").

Requires: docker compose db service running, the catalog already synced
and described (prior slices), a working ANTHROPIC_API_KEY/VOYAGE_API_KEY
in .env, and a real evals/questions.yaml with hand-verified questions --
it makes one real, sequential, billed Anthropic call and one real Voyage
embedding call per question (via generate_sql()), plus one real execute
per question against the read-only asyncpg connection.

This does not assert any particular accuracy score (the brief explicitly
allows "or honestly fewer" than a perfect score) -- only that the command
exits 0 and reports a real, well-formed summary and per-question result
lines, per the Outputs' "prints a per-question PASS/FAIL line and a final
'N/M correct' summary".

Will fail honestly until evals/run.py and evals/questions.yaml both exist.
"""
import re
import unittest

from _catalog_helpers import run_sync
from _describe_helpers import run_describe
from _eval_helpers import run_evals


class EvalRunDoneCheckTests(unittest.TestCase):
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
                "python -m evals.run cannot be exercised against a fully "
                f"described catalog:\nstdout={self.describe_result.stdout}\n"
                f"stderr={self.describe_result.stderr}"
            )

    def test_evals_run_exits_zero(self):
        self._require_described_catalog()

        result = run_evals()
        self.assertEqual(
            result.returncode,
            0,
            "python -m evals.run did not exit 0 (the brief's done-check):\n"
            f"stdout={result.stdout}\nstderr={result.stderr}",
        )

    def test_evals_run_stdout_reports_an_n_out_of_m_correct_summary(self):
        # Not hardcoded to /5: evals/questions.yaml has grown to 6 since
        # the glossary-retrieval slice (plans/briefs/2026-08-03-glossary-
        # retrieval.md) added a 6th question, and templates/eval.md's own
        # "start with 5; every production/demo failure adds a case"
        # lifecycle means the denominator keeps growing legitimately.
        self._require_described_catalog()

        result = run_evals()
        self.assertRegex(
            result.stdout,
            re.compile(r"\d+/\d+ correct", re.IGNORECASE),
            "expected an 'N/M correct' style summary line in stdout "
            f"(the brief allows any real score, not necessarily a perfect "
            f"one):\nstdout={result.stdout}",
        )

    def test_evals_run_stdout_reports_a_pass_or_fail_line_per_question(self):
        self._require_described_catalog()

        result = run_evals()
        pass_or_fail_marks = len(re.findall(r"PASS|FAIL", result.stdout, re.IGNORECASE))
        self.assertGreaterEqual(
            pass_or_fail_marks,
            5,
            "expected at least 5 PASS/FAIL markers in stdout, one per "
            f"curated question:\nstdout={result.stdout}",
        )


if __name__ == "__main__":
    unittest.main()
