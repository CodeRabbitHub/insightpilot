"""
Structural checks for `evals/questions.yaml` per the eval-harness-v1
brief's Constraints/Outputs (plans/briefs/2026-08-02-eval-harness-v1.md):
"Start with exactly 5 questions"; "Each question needs a real
expected-result assertion ... hand-verified against the real `olist`
database ... never invented or copied from an LLM's guess"; "Grading is
exact-match or code-assertion only, no LLM-as-judge".

This test-writing role is deliberately blind to the actual 5 questions'
content (hand-verifying them against the real database is the
implementer's job for this slice, not something to invent here) -- only
the file's shape is checked: it exists, parses as YAML, has exactly 5
entries, and every entry carries a non-empty question string plus a
structured (never free-text/prose) expected assertion, since exact-match/
code-assertion grading is impossible against a prose expectation.

Will fail honestly until evals/questions.yaml exists with this shape.
"""
import unittest

import yaml

from _pg_helpers import REPO_ROOT

QUESTIONS_FILE = REPO_ROOT / "evals" / "questions.yaml"


class EvalQuestionsYamlTests(unittest.TestCase):
    def _load(self):
        self.assertTrue(
            QUESTIONS_FILE.exists(),
            "evals/questions.yaml is missing -- the brief requires 5 "
            "curated questions with real, hand-verified expected "
            "assertions",
        )
        with QUESTIONS_FILE.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)

    def test_file_parses_as_valid_yaml_into_a_list(self):
        data = self._load()
        self.assertIsInstance(
            data,
            list,
            f"evals/questions.yaml must parse to a YAML list, got: {type(data)}",
        )

    def test_starts_with_exactly_five_questions(self):
        # Per the brief's Constraints: "Start with exactly 5 questions,
        # per templates/eval.md's 'start with 5' and PRD.md Section 10's
        # eventual 30 being an M8 (not M3) target."
        data = self._load()
        self.assertEqual(
            len(data),
            5,
            f"evals/questions.yaml must start with exactly 5 questions "
            f"(the eventual 30 is an M8 target, not this M3 slice), got "
            f"{len(data)}",
        )

    def test_every_question_has_a_nonblank_question_string(self):
        data = self._load()
        for i, case in enumerate(data):
            self.assertIsInstance(
                case,
                dict,
                f"question #{i + 1} is not a mapping: {case!r}",
            )
            self.assertIn(
                "question",
                case,
                f"question #{i + 1} has no 'question' key: {case!r}",
            )
            self.assertTrue(
                str(case["question"]).strip(),
                f"question #{i + 1} has a blank 'question' value: {case!r}",
            )

    def test_every_question_has_a_structured_code_checkable_expected_assertion(self):
        # Grading is exact-match/code-assertion only (no LLM-as-judge), so
        # 'expected' must be a real structured value (a mapping, per the
        # brief's own proposed shape, e.g. {top_row: [...]}), never a bare
        # prose string a human/LLM would have to "judge".
        data = self._load()
        for i, case in enumerate(data):
            self.assertIn(
                "expected",
                case,
                f"question #{i + 1} has no 'expected' assertion: {case!r}",
            )
            expected = case["expected"]
            self.assertIsInstance(
                expected,
                dict,
                f"question #{i + 1}'s 'expected' must be a structured "
                f"mapping (code-checkable), not free text: {expected!r}",
            )
            self.assertGreater(
                len(expected),
                0,
                f"question #{i + 1}'s 'expected' mapping is empty: {case!r}",
            )

    def test_all_five_questions_are_distinct(self):
        data = self._load()
        question_texts = [str(case["question"]).strip() for case in data]
        self.assertEqual(
            len(question_texts),
            len(set(question_texts)),
            f"evals/questions.yaml has duplicate questions: {question_texts}",
        )


if __name__ == "__main__":
    unittest.main()
