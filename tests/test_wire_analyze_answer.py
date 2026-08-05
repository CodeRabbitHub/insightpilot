"""
Tests for the wire-analyze-answer brief
(plans/briefs/2026-08-05-wire-analyze-answer.md): `app.pipeline.answer.
get_answer()` is extended to call the already-proven
`app.pipeline.analyze_answer.analyze_answer(question, sql, rows)`
internally, immediately after `_answer_with_repair()` succeeds -- not
left for each of app/main.py's three call sites to invoke separately --
and return a `(sql, rows, analysis)` 3-tuple where `analysis` is a real
`AnalyzeResponse` instance. Per the brief's Outputs, `app.main`'s
`AskResponse`/`ConversationMessageResult` each gain a nested
`analysis: AnalyzeResponse` field, reusing the real model directly.

GetAnswerCallsAnalyzeAnswerSignatureTests is a pure, no-network check:
get_answer()'s own source really does reference analyze_answer(),
mirroring test_answer_repair.py's own
test_get_answer_actually_calls_answer_with_repair precedent for the
prior slice's orchestration seam.

ResponseModelsGainAnalysisFieldTests are pure, no-network checks on
app.main's Pydantic response models: AskResponse and
ConversationMessageResult must each declare a real
`analysis: AnalyzeResponse` field (reusing the real model directly, per
templates/no-slop.md item 7 -- never a hand-flattened duplicate field
set, never a raw dict), independent of any real HTTP call.

GetAnswerAnalysisEndToEndTests proves the wired contract for real: ONE
real get_answer(FIXED_QUESTION) call (two Voyage embeds, one Anthropic
call for SQL generation, and -- once this brief is wired in -- one more
real Anthropic call for the analysis step), shared across every test in
the class via setUpClass, never repeated per test, mirroring this repo's
existing shared-setUpClass convention (test_answer_repair.py's
AnswerWithRepairEndToEndTests, test_analyze_answer.py's
AnalyzeAnswerEndToEndTests).

GetAnswerPropagatesAnalyzeAnswerFailureTests proves the brief's explicit
Constraint that an analyze_answer() failure propagates uncaught out of
get_answer() -- "no partial/degraded response, no silent fallback" --
by patching `app.pipeline.answer.analyze_answer` (the one seam
get_answer() now owns) to raise, around one real generate_sql()+
execute() call (so sql/rows genuinely succeed first), proving the
failure surfaces from get_answer() itself and not only through
app/main.py's 502-mapping (which test_api_ask.py/test_api_ask_stream.py/
test_api_conversations.py already cover via the same
`patch("app.main.get_answer", ...)` seam, at the HTTP layer).

Requires: docker compose db service running, the catalog already synced
and described (prior slices), and working ANTHROPIC_API_KEY/
VOYAGE_API_KEY values in .env for the end-to-end classes -- both make
real, billed API calls.

Will fail honestly until app/pipeline/answer.py's get_answer() calls
analyze_answer() internally and returns the new 3-tuple, and app/main.py's
AskResponse/ConversationMessageResult gain their analysis field.
"""
import asyncio
import inspect
import unittest
from unittest.mock import patch

from _catalog_helpers import run_sync
from _describe_helpers import run_describe

from app.pipeline import answer
from app.pipeline.generate_sql import FIXED_QUESTION


class GetAnswerCallsAnalyzeAnswerSignatureTests(unittest.TestCase):
    """Pure, no-network check: get_answer()'s own source really does
    call analyze_answer(), independent of what any real call returns --
    mirrors test_answer_repair.py's
    test_get_answer_actually_calls_answer_with_repair precedent."""

    def test_get_answer_source_references_analyze_answer(self):
        source = inspect.getsource(answer.get_answer)
        self.assertIn(
            "analyze_answer",
            source,
            "get_answer() must call analyze_answer() itself, internally, "
            "immediately after a successful validate+execute, per the "
            "brief's Constraints -- its source does not reference it:\n"
            f"{source}",
        )


class ResponseModelsGainAnalysisFieldTests(unittest.TestCase):
    """Pure, no-network checks on app.main's Pydantic response models:
    AskResponse and ConversationMessageResult must each declare a real
    `analysis: AnalyzeResponse` field, independent of any real HTTP
    call."""

    def test_ask_response_declares_an_analysis_field(self):
        from app.main import AskResponse

        self.assertIn(
            "analysis",
            AskResponse.model_fields,
            "AskResponse has no 'analysis' field -- the brief requires "
            f"one, got fields: {list(AskResponse.model_fields)!r}",
        )

    def test_ask_response_analysis_field_is_typed_as_the_real_analyze_response(self):
        from app.main import AskResponse
        from app.pipeline.analyze_answer import AnalyzeResponse

        self.assertIs(
            AskResponse.model_fields["analysis"].annotation,
            AnalyzeResponse,
            "AskResponse.analysis must be typed as the real "
            "app.pipeline.analyze_answer.AnalyzeResponse model directly, "
            "per the brief's Constraints (never hand-flattened, never a "
            "raw dict merge), got: "
            f"{AskResponse.model_fields['analysis'].annotation!r}",
        )

    def test_conversation_message_result_declares_an_analysis_field(self):
        from app.main import ConversationMessageResult

        self.assertIn(
            "analysis",
            ConversationMessageResult.model_fields,
            "ConversationMessageResult has no 'analysis' field -- the "
            "brief requires one, got fields: "
            f"{list(ConversationMessageResult.model_fields)!r}",
        )

    def test_conversation_message_result_analysis_field_is_typed_as_the_real_analyze_response(
        self,
    ):
        from app.main import ConversationMessageResult
        from app.pipeline.analyze_answer import AnalyzeResponse

        self.assertIs(
            ConversationMessageResult.model_fields["analysis"].annotation,
            AnalyzeResponse,
            "ConversationMessageResult.analysis must be typed as the "
            "real app.pipeline.analyze_answer.AnalyzeResponse model "
            "directly, got: "
            f"{ConversationMessageResult.model_fields['analysis'].annotation!r}",
        )


class GetAnswerAnalysisEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sync_result = run_sync()
        cls.describe_result = run_describe()
        cls.result = None
        cls.error = None
        if cls.sync_result.returncode == 0 and cls.describe_result.returncode == 0:
            try:
                # One real, billed chain (two Voyage embeds, one
                # Anthropic call for SQL generation, and -- once this
                # brief is wired in -- one more real Anthropic call for
                # the analysis step), shared across every test in this
                # class.
                cls.result = asyncio.run(answer.get_answer(FIXED_QUESTION))
            except Exception as exc:  # noqa: BLE001 -- captured, not swallowed
                cls.error = exc

    def setUp(self):
        if self.sync_result.returncode != 0:
            self.fail(
                "python -m app.catalog.sync did not exit 0:\n"
                f"stdout={self.sync_result.stdout}\nstderr={self.sync_result.stderr}"
            )
        if self.describe_result.returncode != 0:
            self.fail(
                "python -m app.catalog.describe did not exit 0:\n"
                f"stdout={self.describe_result.stdout}\n"
                f"stderr={self.describe_result.stderr}"
            )
        if self.error is not None:
            self.fail(
                f"get_answer({FIXED_QUESTION!r}) raised instead of "
                f"returning a result: {self.error!r}"
            )
        self.assertIsNotNone(
            self.result,
            "no result was captured -- see the other failures above",
        )

    def test_get_answer_returns_a_3_tuple(self):
        self.assertEqual(
            len(self.result),
            3,
            "expected get_answer() to return a (sql, rows, analysis) "
            f"3-tuple per the brief's Constraints, got: {self.result!r}",
        )

    def test_third_element_is_a_real_analyze_response_instance(self):
        from app.pipeline.analyze_answer import AnalyzeResponse

        _sql, _rows, analysis = self.result
        self.assertIsInstance(
            analysis,
            AnalyzeResponse,
            "expected get_answer()'s third return value to be a real "
            f"AnalyzeResponse instance, got: {analysis!r}",
        )

    def test_analysis_summary_is_a_nonblank_string(self):
        _sql, _rows, analysis = self.result
        self.assertIsInstance(analysis.summary, str)
        self.assertTrue(
            analysis.summary.strip(),
            "get_answer()'s analysis.summary was blank",
        )

    def test_analysis_explanation_is_a_nonblank_string(self):
        _sql, _rows, analysis = self.result
        self.assertIsInstance(analysis.explanation, str)
        self.assertTrue(
            analysis.explanation.strip(),
            "get_answer()'s analysis.explanation was blank",
        )

    def test_analysis_chart_spec_is_a_dict(self):
        _sql, _rows, analysis = self.result
        self.assertIsInstance(analysis.chart_spec, dict)

    def test_analysis_follow_ups_is_a_nonempty_list_of_nonblank_strings(self):
        _sql, _rows, analysis = self.result
        self.assertIsInstance(analysis.follow_ups, list)
        self.assertGreater(
            len(analysis.follow_ups),
            0,
            "get_answer()'s analysis.follow_ups was empty -- PRD F1 "
            "requires 3-5 suggested follow-up questions",
        )
        for item in analysis.follow_ups:
            self.assertIsInstance(item, str)
            self.assertTrue(item.strip())

    def test_sql_and_rows_are_still_a_real_select_and_nonempty_rows(self):
        # The brief's Constraint that analyze_answer() runs only AFTER a
        # successful (sql, rows) -- proves this slice didn't regress the
        # existing sql/rows contract while adding the third element.
        sql, rows, _analysis = self.result
        self.assertIsInstance(sql, str)
        self.assertTrue(sql.strip().upper().startswith("SELECT"))
        self.assertIsInstance(rows, list)
        self.assertGreater(len(rows), 0)


class GetAnswerPropagatesAnalyzeAnswerFailureTests(unittest.TestCase):
    """Proves the brief's explicit Constraint: 'If analyze_answer()
    raises (LLM failure after its own exhausted retry), that failure
    propagates uncaught out of get_answer() exactly like an unrepaired
    validate_sql()/execute_sql() failure already does today -- no
    partial/degraded response, no silent fallback.' Patches
    `app.pipeline.answer.analyze_answer` (the one seam get_answer() now
    owns) to raise, around one real generate_sql()+execute() call, so
    sql/rows genuinely succeed first and the failure is proven to come
    from the analysis step specifically, not the repair loop."""

    @classmethod
    def setUpClass(cls):
        cls.sync_result = run_sync()
        cls.describe_result = run_describe()

    def setUp(self):
        if self.sync_result.returncode != 0:
            self.fail(
                "python -m app.catalog.sync did not exit 0:\n"
                f"stdout={self.sync_result.stdout}\nstderr={self.sync_result.stderr}"
            )
        if self.describe_result.returncode != 0:
            self.fail(
                "python -m app.catalog.describe did not exit 0:\n"
                f"stdout={self.describe_result.stdout}\n"
                f"stderr={self.describe_result.stderr}"
            )

    def test_an_analyze_answer_failure_propagates_uncaught_from_get_answer(self):
        simulated_error = RuntimeError(
            "simulated analyze_answer failure: LLM exhausted its retry"
        )
        with patch(
            "app.pipeline.answer.analyze_answer", side_effect=simulated_error
        ):
            with self.assertRaises(RuntimeError) as ctx:
                # One real, billed generate_sql()+execute() call -- sql/
                # rows genuinely succeed; only the mocked analysis step
                # fails.
                asyncio.run(answer.get_answer(FIXED_QUESTION))

        self.assertIs(
            ctx.exception,
            simulated_error,
            "expected the exact analyze_answer() failure to propagate "
            "unmodified out of get_answer() -- not wrapped, not "
            "swallowed, not replaced by a partial/degraded response, "
            f"got: {ctx.exception!r}",
        )


if __name__ == "__main__":
    unittest.main()
