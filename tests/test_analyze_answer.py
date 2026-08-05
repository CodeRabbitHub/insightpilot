"""
Tests for the analyze_answer pipeline step brief
(plans/briefs/2026-08-05-analyze-answer.md): a new
`app.pipeline.analyze_answer.analyze_answer(question, sql, rows)` makes
one real Claude call with the question, the executed SQL, and a capped
sample of its result rows, returning a Pydantic-validated
`AnalyzeResponse` with fields `summary: str`, `explanation: str`,
`chart_spec: dict[str, Any]`, `follow_ups: list[str]`.

AnalyzeAnswerSignatureTests and AnalyzeResponseModelTests are pure,
no-network checks (signature shape, and the Pydantic model's own field
validation), independent of what any real call returns.

AnalyzeAnswerEndToEndTests proves the real, wired contract: a real
get_answer() call (from app.pipeline.answer) for the real FIXED_QUESTION
(from app.pipeline.generate_sql) produces a real (sql, rows) pair -- not
hand-faked input -- which is then fed through one real, billed
analyze_answer() call, shared across every test in the class via
setUpClass (mirrors test_repair_sql.py's RepairSqlEndToEndTests
precedent: one real call per class, never repeated per-test).

Per the wire-analyze-answer brief
(plans/briefs/2026-08-05-wire-analyze-answer.md), get_answer() itself now
also returns an internally-computed analysis as a third tuple element --
setUpClass below unpacks that third element (captured, deliberately not
asserted on here; that wiring's own behavior is covered by
tests/test_wire_analyze_answer.py) so this file's own unpacking still
matches get_answer()'s real return shape.

AnalyzeAnswerRowSampleCappingTests exercises the brief's row-capping
Constraint ("do not serialize the full up-to-1000-row result into the
prompt") behaviorally: a hand-crafted row list well beyond a small sample
must not make analyze_answer() blow up, without asserting any specific
cap number -- the brief leaves the exact cap size to be finalized at
Gate 1, not this test-writing role.

Requires: docker compose db service running, the catalog already synced
and described (prior slices), and working ANTHROPIC_API_KEY/
VOYAGE_API_KEY values in .env for the end-to-end classes -- both make
real, billed API calls.

Will fail honestly until app/pipeline/analyze_answer.py exists.
"""
import asyncio
import inspect
import json
import unittest

from _catalog_helpers import run_sync
from _describe_helpers import run_describe


class AnalyzeAnswerSignatureTests(unittest.TestCase):
    """Pure, no-network check: analyze_answer() has the exact signature
    the brief's Outputs section names, independent of what any real call
    returns."""

    def test_analyze_answer_has_the_brief_signature(self):
        from app.pipeline import analyze_answer as module

        sig = inspect.signature(module.analyze_answer)
        self.assertEqual(
            list(sig.parameters),
            ["question", "sql", "rows"],
            "analyze_answer() must accept exactly (question, sql, rows) "
            f"per the brief's Outputs section, got {list(sig.parameters)!r}",
        )


class AnalyzeResponseModelTests(unittest.TestCase):
    """Pure, no-network checks on the AnalyzeResponse Pydantic model
    itself: field shapes and the brief's explicit validation rules
    (chart_spec present as a JSON object, follow_ups a *non-empty* list
    of strings) -- independent of any real LLM call."""

    def test_a_valid_payload_round_trips_through_every_declared_field(self):
        from app.pipeline.analyze_answer import AnalyzeResponse

        model = AnalyzeResponse(
            summary="bed_bath_table is the top category by order count.",
            explanation="The query groups order_items by product category "
            "and counts distinct orders per category.",
            chart_spec={"type": "bar", "x": "category", "y": "num_orders"},
            follow_ups=[
                "How does this compare to last year?",
                "Which category has the highest average order value?",
            ],
        )
        self.assertEqual(
            model.summary, "bed_bath_table is the top category by order count."
        )
        self.assertEqual(
            model.explanation,
            "The query groups order_items by product category and counts "
            "distinct orders per category.",
        )
        self.assertEqual(
            model.chart_spec, {"type": "bar", "x": "category", "y": "num_orders"}
        )
        self.assertEqual(
            model.follow_ups,
            [
                "How does this compare to last year?",
                "Which category has the highest average order value?",
            ],
        )

    def test_chart_spec_accepts_an_arbitrary_json_object_shape(self):
        # chart_spec's concrete chart-type/axis-mapping schema is
        # deliberately out of scope this slice -- only "a JSON object" is
        # validated, so an arbitrary/nested dict shape must be accepted.
        from app.pipeline.analyze_answer import AnalyzeResponse

        model = AnalyzeResponse(
            summary="s",
            explanation="e",
            chart_spec={"anything": [1, 2, {"nested": True}], "another_key": None},
            follow_ups=["one follow-up?"],
        )
        self.assertIsInstance(model.chart_spec, dict)

    def test_chart_spec_must_be_a_dict(self):
        from pydantic import ValidationError

        from app.pipeline.analyze_answer import AnalyzeResponse

        with self.assertRaises(ValidationError):
            AnalyzeResponse(
                summary="s",
                explanation="e",
                chart_spec="not a dict",
                follow_ups=["one follow-up?"],
            )

    def test_an_empty_follow_ups_list_is_rejected(self):
        # PRD F1: "3-5 suggested follow-up questions" -- the brief
        # requires follow_ups to validate as a *non-empty* list of
        # strings, which a bare `list[str]` type annotation alone would
        # not enforce.
        from pydantic import ValidationError

        from app.pipeline.analyze_answer import AnalyzeResponse

        with self.assertRaises(ValidationError):
            AnalyzeResponse(
                summary="s", explanation="e", chart_spec={}, follow_ups=[]
            )

    def test_follow_ups_must_contain_only_strings(self):
        from pydantic import ValidationError

        from app.pipeline.analyze_answer import AnalyzeResponse

        with self.assertRaises(ValidationError):
            AnalyzeResponse(
                summary="s",
                explanation="e",
                chart_spec={},
                follow_ups=[{"not": "a string"}],
            )

    def test_missing_summary_is_rejected(self):
        from pydantic import ValidationError

        from app.pipeline.analyze_answer import AnalyzeResponse

        with self.assertRaises(ValidationError):
            AnalyzeResponse(explanation="e", chart_spec={}, follow_ups=["x?"])

    def test_missing_explanation_is_rejected(self):
        from pydantic import ValidationError

        from app.pipeline.analyze_answer import AnalyzeResponse

        with self.assertRaises(ValidationError):
            AnalyzeResponse(summary="s", chart_spec={}, follow_ups=["x?"])

    def test_missing_chart_spec_is_rejected(self):
        from pydantic import ValidationError

        from app.pipeline.analyze_answer import AnalyzeResponse

        with self.assertRaises(ValidationError):
            AnalyzeResponse(summary="s", explanation="e", follow_ups=["x?"])

    def test_missing_follow_ups_is_rejected(self):
        from pydantic import ValidationError

        from app.pipeline.analyze_answer import AnalyzeResponse

        with self.assertRaises(ValidationError):
            AnalyzeResponse(summary="s", explanation="e", chart_spec={})


class BuildPromptRowCappingTests(unittest.TestCase):
    """Pure, no-network checks: the brief's Constraint ("do not serialize
    the full up-to-1000-row result into the prompt... capped to a small
    sample") is verified structurally here, by inspecting build_prompt()'s
    actual output -- not just behaviorally (AnalyzeAnswerRowSampleCappingTests
    below only proves a large input doesn't crash analyze_answer(), which
    would still pass even if capping were silently removed)."""

    def test_build_prompt_caps_the_serialized_row_sample_to_row_sample_cap(self):
        from app.pipeline.analyze_answer import ROW_SAMPLE_CAP, build_prompt

        large_row_count = ROW_SAMPLE_CAP + 50
        rows = [{"category": f"cat_{i}", "count": i} for i in range(large_row_count)]

        prompt = build_prompt("How many per category?", "SELECT 1", rows)
        sample_json = prompt.split("as JSON):\n", 1)[1]
        sample = json.loads(sample_json)

        self.assertEqual(
            len(sample),
            ROW_SAMPLE_CAP,
            f"build_prompt() serialized {len(sample)} rows into the prompt "
            f"for a {large_row_count}-row input -- expected exactly "
            f"ROW_SAMPLE_CAP ({ROW_SAMPLE_CAP}) rows",
        )
        self.assertEqual(sample, rows[:ROW_SAMPLE_CAP])

    def test_build_prompt_reports_the_true_total_row_count_alongside_the_capped_sample(
        self,
    ):
        from app.pipeline.analyze_answer import ROW_SAMPLE_CAP, build_prompt

        large_row_count = ROW_SAMPLE_CAP + 50
        rows = [{"category": f"cat_{i}", "count": i} for i in range(large_row_count)]

        prompt = build_prompt("How many per category?", "SELECT 1", rows)
        self.assertIn(f"({ROW_SAMPLE_CAP} of {large_row_count}", prompt)

    def test_build_prompt_handles_an_empty_row_list_without_raising(self):
        from app.pipeline.analyze_answer import build_prompt

        prompt = build_prompt("Any orders at all?", "SELECT 1 WHERE FALSE", [])
        self.assertIn("(0 of 0", prompt)
        self.assertIn("[]", prompt)


class AnalyzeAnswerEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sync_result = run_sync()
        cls.describe_result = run_describe()
        cls.question = None
        cls.sql = None
        cls.rows = None
        cls.get_answer_analysis = None
        cls.get_answer_error = None
        cls.result = None
        if cls.sync_result.returncode == 0 and cls.describe_result.returncode == 0:
            from app.pipeline.answer import get_answer
            from app.pipeline.generate_sql import FIXED_QUESTION

            cls.question = FIXED_QUESTION
            try:
                # One real, billed chain (two Voyage embeds + one
                # Anthropic call), shared across every test in this
                # class -- never repeated per-test. get_answer() itself
                # now also returns a third, internally-computed analysis
                # element (plans/briefs/2026-08-05-wire-analyze-answer.md)
                # -- captured here but not asserted on; that wiring's own
                # behavior is covered by test_wire_analyze_answer.py, not
                # this file, which is scoped to analyze_answer() itself.
                cls.sql, cls.rows, cls.get_answer_analysis = asyncio.run(
                    get_answer(cls.question)
                )
            except Exception as exc:  # pragma: no cover - environment/network
                cls.get_answer_error = exc

            if cls.get_answer_error is None:
                from app.pipeline.analyze_answer import analyze_answer

                # A second real, billed Anthropic call, likewise shared
                # across every test in this class.
                cls.result = analyze_answer(cls.question, cls.sql, cls.rows)

    def setUp(self):
        if self.sync_result.returncode != 0:
            self.fail(
                "python -m app.catalog.sync did not exit 0:\n"
                f"stdout={self.sync_result.stdout}\nstderr={self.sync_result.stderr}"
            )
        if self.describe_result.returncode != 0:
            self.fail(
                "python -m app.catalog.describe did not exit 0, so "
                "get_answer() cannot be exercised against a fully-"
                f"described catalog:\nstdout={self.describe_result.stdout}\n"
                f"stderr={self.describe_result.stderr}"
            )
        if self.get_answer_error is not None:
            self.fail(
                "get_answer() raised for the fixed question, so "
                "analyze_answer() could not be exercised end-to-end with "
                f"a real (sql, rows) pair: {self.get_answer_error!r}"
            )

    def test_analyze_answer_returns_an_analyze_response_instance(self):
        from app.pipeline.analyze_answer import AnalyzeResponse

        self.assertIsInstance(self.result, AnalyzeResponse)

    def test_summary_is_a_nonblank_string(self):
        self.assertIsInstance(self.result.summary, str)
        self.assertTrue(
            self.result.summary.strip(), "analyze_answer() returned a blank summary"
        )

    def test_explanation_is_a_nonblank_string(self):
        self.assertIsInstance(self.result.explanation, str)
        self.assertTrue(
            self.result.explanation.strip(),
            "analyze_answer() returned a blank explanation",
        )

    def test_chart_spec_is_a_dict(self):
        self.assertIsInstance(self.result.chart_spec, dict)

    def test_follow_ups_is_a_nonempty_list_of_nonblank_strings(self):
        self.assertIsInstance(self.result.follow_ups, list)
        self.assertGreater(
            len(self.result.follow_ups),
            0,
            "analyze_answer() returned an empty follow_ups list -- PRD F1 "
            "requires 3-5 suggested follow-up questions",
        )
        for item in self.result.follow_ups:
            self.assertIsInstance(item, str)
            self.assertTrue(item.strip())


class AnalyzeAnswerRowSampleCappingTests(unittest.TestCase):
    """Constraints: 'do not serialize the full up-to-1000-row result into
    the prompt.' A hand-crafted row list well beyond a small sample size
    (the brief's own candidate cap is 20; PRD F1's display cap is 50)
    exercises analyze_answer()'s row-capping behavior directly: it must
    still complete and return a valid AnalyzeResponse, not choke on (or
    blindly forward the entirety of) a large row list. No specific cap
    number is asserted -- that's left to be finalized at Gate 1."""

    LARGE_ROW_COUNT = 200

    @classmethod
    def setUpClass(cls):
        cls.question = "How many orders are there per product category?"
        cls.sql = (
            "SELECT product_category_name, COUNT(*) AS num_orders "
            "FROM olist.order_items GROUP BY product_category_name"
        )
        cls.rows = [
            {"product_category_name": f"category_{i}", "num_orders": i}
            for i in range(cls.LARGE_ROW_COUNT)
        ]
        cls.result = None
        cls.error = None
        try:
            from app.pipeline.analyze_answer import analyze_answer

            # One real, billed Anthropic call, shared across every test
            # in this class.
            cls.result = analyze_answer(cls.question, cls.sql, cls.rows)
        except Exception as exc:  # pragma: no cover - environment/network
            cls.error = exc

    def test_a_row_sample_larger_than_a_small_sample_does_not_raise(self):
        if self.error is not None:
            self.fail(
                f"analyze_answer() raised for a {self.LARGE_ROW_COUNT}-row "
                "input -- the brief requires result rows to be capped to "
                "a small sample before being serialized into the prompt, "
                f"not forwarded in full: {self.error!r}"
            )

    def test_a_row_sample_larger_than_a_small_sample_still_returns_a_valid_response(
        self,
    ):
        if self.error is not None:
            self.skipTest(f"analyze_answer() raised: {self.error!r}")
        from app.pipeline.analyze_answer import AnalyzeResponse

        self.assertIsInstance(self.result, AnalyzeResponse)
        self.assertTrue(self.result.summary.strip())
        self.assertTrue(self.result.explanation.strip())
        self.assertIsInstance(self.result.chart_spec, dict)
        self.assertGreater(len(self.result.follow_ups), 0)


if __name__ == "__main__":
    unittest.main()
