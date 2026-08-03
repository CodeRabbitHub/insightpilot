"""
Pure, no-network/no-DB unit tests for the eval-harness-v1 brief's runner
(plans/briefs/2026-08-02-eval-harness-v1.md): `evals/run.py` loads
`evals/questions.yaml`, calls `answer.get_answer(question)` per question,
checks the result against its expected assertion, and prints a
per-question PASS/FAIL line plus a final "N/5 correct" summary.

Per the brief's own Tests requirement -- "the eval runner correctly
reports pass/fail against a known-good and a known-bad fixture case
... testable as a pure function over synthetic data, no real API/DB
needed" (matching this project's existing precedent of pure unit tests
for pydantic validators, e.g. GenerateSqlResponseValidatorTests in
test_generate_sql_cli.py) -- this exercises `evals.run`'s grading and
loading logic directly against hand-built fixtures, never against a real
`answer.get_answer()` call or a live database.

This is the test-writer's chosen minimal contract for evals/run.py,
inferred directly from the brief's explicit request for pure-function
testability (the brief names no exact function signature itself):

  - `load_questions(path)` -- parses a questions.yaml-shaped file into a
    list of question dicts (each with 'question'/'expected' keys),
    preserving file order.
  - `check_expected(rows, expected)` -- grades one question's real result
    rows (the list-of-dict shape `execute_sql()`/`get_answer()` return)
    against its `expected` assertion mapping, returning True/False and
    never raising for a mismatch (so the runner's per-question loop can
    report PASS/FAIL for every case without a try/except around each
    one).
  - `format_summary(num_correct, total)` -- the exact "N/5 correct"
    style summary string.

Will fail honestly (ImportError) until evals/run.py (and evals/__init__.py,
if needed for the package import below) exist with this shape.
"""
import tempfile
import unittest
from pathlib import Path

from evals import run as eval_run


class LoadQuestionsTests(unittest.TestCase):
    """load_questions() must be a real YAML loader, not a hardcoded stub
    -- proven by round-tripping a hand-built temp fixture file, never the
    real evals/questions.yaml (whose content is out of this test-writing
    role's hands and may not exist yet)."""

    def _write_temp_yaml(self, text):
        tmp_dir = Path(tempfile.mkdtemp())
        tmp_path = tmp_dir / "fixture_questions.yaml"
        tmp_path.write_text(text, encoding="utf-8")
        return tmp_path

    def test_loads_a_list_of_question_dicts_in_file_order(self):
        fixture = self._write_temp_yaml(
            "- question: \"What is the total row count of orders?\"\n"
            "  expected:\n"
            "    top_row: [\"count\", 99000]\n"
            "- question: \"What is the top category by order count?\"\n"
            "  expected:\n"
            "    top_row: [\"beleza_saude\", 8836]\n"
        )
        questions = eval_run.load_questions(fixture)

        self.assertEqual(
            len(questions),
            2,
            f"expected 2 loaded questions, got: {questions!r}",
        )
        self.assertEqual(
            questions[0]["question"],
            "What is the total row count of orders?",
        )
        self.assertEqual(
            questions[1]["question"],
            "What is the top category by order count?",
        )
        self.assertEqual(
            questions[0]["expected"],
            {"top_row": ["count", 99000]},
        )

    def test_loads_a_single_question_file_as_a_one_item_list(self):
        fixture = self._write_temp_yaml(
            "- question: \"Only one here\"\n"
            "  expected:\n"
            "    top_row: [\"x\", 1]\n"
        )
        questions = eval_run.load_questions(fixture)
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]["question"], "Only one here")


class CheckExpectedGradingTests(unittest.TestCase):
    """Pure grading logic over synthetic (never real-DB) rows -- a known
    -good fixture must grade True/PASS, a known-bad fixture (same
    expected assertion, wrong actual data) must grade False/FAIL. This is
    the exact behavior the brief's Tests section asks for."""

    EXPECTED = {"top_row": ["beleza_saude", 8836]}

    def test_a_known_good_fixture_case_passes(self):
        rows = [
            {"product_category_name": "beleza_saude", "num_orders": 8836},
            {"product_category_name": "cama_mesa_banho", "num_orders": 7000},
        ]
        self.assertTrue(
            eval_run.check_expected(rows, self.EXPECTED),
            f"expected rows matching {self.EXPECTED!r} to grade as a "
            f"pass, got rows: {rows!r}",
        )

    def test_a_known_bad_fixture_case_with_a_wrong_top_value_fails(self):
        rows = [
            {"product_category_name": "cama_mesa_banho", "num_orders": 9417},
            {"product_category_name": "beleza_saude", "num_orders": 8836},
        ]
        self.assertFalse(
            eval_run.check_expected(rows, self.EXPECTED),
            f"expected rows NOT matching {self.EXPECTED!r} (wrong top "
            f"row) to grade as a fail, got rows: {rows!r}",
        )

    def test_a_known_bad_fixture_case_with_a_wrong_count_fails(self):
        rows = [
            {"product_category_name": "beleza_saude", "num_orders": 1},
        ]
        self.assertFalse(
            eval_run.check_expected(rows, self.EXPECTED),
            "expected a right-category-wrong-count row to grade as a "
            f"fail, got rows: {rows!r}",
        )

    def test_empty_rows_fail_rather_than_raise(self):
        try:
            result = eval_run.check_expected([], self.EXPECTED)
        except Exception as exc:  # pragma: no cover - failure path
            self.fail(
                "check_expected() must grade a no-rows result as a plain "
                f"failure, not raise: {exc!r}"
            )
        self.assertFalse(result)


class FormatSummaryTests(unittest.TestCase):
    """The runner's final line is a real 'N/5 correct' summary, per the
    brief's Outputs -- a pure string-formatting check, independent of any
    real question count."""

    def test_all_correct(self):
        self.assertEqual(eval_run.format_summary(5, 5), "5/5 correct")

    def test_some_incorrect(self):
        self.assertEqual(eval_run.format_summary(2, 5), "2/5 correct")

    def test_none_correct(self):
        self.assertEqual(eval_run.format_summary(0, 5), "0/5 correct")


if __name__ == "__main__":
    unittest.main()
