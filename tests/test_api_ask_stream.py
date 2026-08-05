"""
Tests for the FastAPI /api/ask/stream endpoint brief
(plans/briefs/2026-08-04-fastapi-ask-stream-endpoint.md): a second,
additive route on the existing `app/main.py` that runs the same
`app.pipeline.answer.get_answer(question)` call as `/api/ask` but
delivers its single eventual outcome as a Server-Sent Events (SSE)
response instead of a plain JSON body, per ARCHITECT.md's "SSE, not
WebSockets, for streaming" decision.

Per the brief's Outputs: request `{"question": str}` -> always HTTP 200
(the SSE stream transport itself succeeded), with the outcome signaled
by the event type in the body instead of the HTTP status code:
- `event: result\ndata: {"sql": str, "rows": [...]}\n\n` on success.
- `event: error\ndata: {"detail": str}\n\n` on any get_answer() failure.

This is a deliberate departure from /api/ask's 502-on-failure contract
(test_api_ask.py) -- the brief is explicit that once the SSE stream has
started, the HTTP status is always 200 regardless of pipeline outcome.

Per the wire-analyze-answer brief
(plans/briefs/2026-08-05-wire-analyze-answer.md), the success `result`
event's exact data key set is updated from {"sql", "rows"} to
{"sql", "rows", "analysis"}, mirroring test_api_ask.py's update to the
same shape.

AskStreamHappyPathTests makes one real call through the real pipeline
(no mocking the LLM/DB), using `app.pipeline.generate_sql.FIXED_QUESTION`
-- this project's existing canonical example question -- and FastAPI's
`TestClient(...).stream(...)` to consume the streamed body, per the
brief's explicit instruction that these tests "make real calls through
the real pipeline (no mocking the LLM/DB)". Follows this repo's shared
setUpClass convention (test_api_ask.py's AskEndpointHappyPathTests):
sync/describe run once per class via _catalog_helpers/_describe_helpers,
and the one real, billed request is made once in setUpClass and shared
across test methods, not repeated per-test.

AskStreamFailurePathTests mirrors test_api_ask.py's
AskEndpointFailurePathTests: a plain fake stands in for get_answer(),
patched at `app.main.get_answer` (the one function app/main.py's stream
handler calls), instead of relying on a real double-LLM repair failure
being reproducible through the NL-question-only HTTP interface. It
asserts the failure surfaces as an `error` SSE event with a non-empty
`detail` string -- not a crash, not a hung stream, and (per the brief)
not an HTTP error status either, since the transport itself succeeded.

Both test classes parse the raw SSE text themselves (split on the
blank-line-separated `event: ...\ndata: ...\n\n` blocks, extract and
json.loads() the `data:` line) rather than relying on any SSE-parsing
helper -- none exists in this codebase or its dependencies per the
brief's constraint against adding `sse-starlette` or similar.

Will fail honestly until app/main.py grows a `/api/ask/stream` route --
no implementation file is created or modified here.
"""
import json
import unittest
from unittest.mock import patch

from _catalog_helpers import run_sync
from _describe_helpers import run_describe

from app.pipeline import generate_sql

try:
    from fastapi.testclient import TestClient

    from app.main import app
except Exception as exc:  # noqa: BLE001 -- captured so setUpClass can report it
    TestClient = None
    app = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


async def _fake_get_answer_that_fails(question):
    raise RuntimeError("simulated repair-loop failure: both attempts failed")


def _parse_sse_events(body_text):
    """Parse a raw SSE body into a list of (event_name, data_dict) pairs.

    Splits on blank-line-separated event blocks (SSE events are
    terminated by a blank line), then within each block finds the
    `event: ...` line and the `data: ...` line and json.loads()s the
    latter. Deliberately hand-rolled per the brief's instruction not to
    invent a nonexistent SSE parsing helper.
    """
    events = []
    blocks = [b for b in body_text.replace("\r\n", "\n").split("\n\n") if b.strip()]
    for block in blocks:
        event_name = None
        data_line = None
        for line in block.split("\n"):
            if line.startswith("event:"):
                event_name = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data_line = line[len("data:"):].strip()
        if event_name is None or data_line is None:
            continue
        events.append((event_name, json.loads(data_line)))
    return events


class AskStreamHappyPathTests(unittest.TestCase):
    """Real question, real pipeline, real HTTP round-trip through
    FastAPI's TestClient's streaming interface -- no mocking of the LLM
    or DB, per the brief's explicit test-convention instruction."""

    @classmethod
    def setUpClass(cls):
        cls.sync_result = run_sync()
        cls.describe_result = run_describe()
        cls.status_code = None
        cls.body_text = None
        cls.request_error = None
        if (
            _IMPORT_ERROR is None
            and cls.sync_result.returncode == 0
            and cls.describe_result.returncode == 0
        ):
            try:
                client = TestClient(app)
                # One real, billed pipeline call (LLM + read-only DB
                # execute, plus -- per the wire-analyze-answer brief --
                # one more real Anthropic call for the analysis step
                # get_answer() now runs internally), shared across every
                # test in this class.
                with client.stream(
                    "POST",
                    "/api/ask/stream",
                    json={"question": generate_sql.FIXED_QUESTION},
                ) as response:
                    cls.status_code = response.status_code
                    cls.body_text = "".join(response.iter_text())
            except Exception as exc:  # noqa: BLE001 -- captured, not swallowed
                cls.request_error = exc

    def setUp(self):
        if _IMPORT_ERROR is not None:
            self.fail(
                f"could not import app.main.app: {_IMPORT_ERROR!r}"
            )
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
        if self.request_error is not None:
            self.fail(
                "POST /api/ask/stream raised instead of streaming a "
                f"response: {self.request_error!r}"
            )
        self.assertIsNotNone(
            self.body_text,
            "no streamed body was captured -- see the other failures above",
        )

    def test_returns_200_for_the_fixed_question(self):
        self.assertEqual(
            self.status_code,
            200,
            "expected 200 for a real, answerable question over SSE, got "
            f"{self.status_code}: {self.body_text}",
        )

    def test_body_contains_exactly_one_result_event(self):
        events = _parse_sse_events(self.body_text)
        result_events = [e for e in events if e[0] == "result"]
        self.assertEqual(
            len(result_events),
            1,
            "expected exactly one 'result' SSE event per the brief's "
            f"Outputs, got events: {events!r}",
        )

    def test_result_event_data_has_exactly_the_sql_rows_and_analysis_keys(self):
        events = _parse_sse_events(self.body_text)
        result_data = next(data for name, data in events if name == "result")
        self.assertEqual(
            set(result_data.keys()),
            {"sql", "rows", "analysis"},
            "expected the result event's data to be exactly "
            "{'sql', 'rows', 'analysis'} per the wire-analyze-answer "
            f"brief's Outputs, got: {result_data!r}",
        )

    def test_result_event_sql_is_a_non_empty_string(self):
        events = _parse_sse_events(self.body_text)
        result_data = next(data for name, data in events if name == "result")
        self.assertIsInstance(result_data["sql"], str)
        self.assertGreater(
            len(result_data["sql"].strip()),
            0,
            f"expected a non-empty SQL string, got: {result_data['sql']!r}",
        )

    def test_result_event_rows_is_a_non_empty_list(self):
        events = _parse_sse_events(self.body_text)
        result_data = next(data for name, data in events if name == "result")
        self.assertIsInstance(result_data["rows"], list)
        self.assertGreater(
            len(result_data["rows"]),
            0,
            f"expected at least one real row back, got: {result_data['rows']!r}",
        )

    def test_result_event_analysis_is_a_dict_with_exactly_the_analyze_response_keys(
        self,
    ):
        events = _parse_sse_events(self.body_text)
        result_data = next(data for name, data in events if name == "result")
        self.assertIsInstance(result_data.get("analysis"), dict)
        self.assertEqual(
            set(result_data["analysis"].keys()),
            {"summary", "explanation", "chart_spec", "follow_ups"},
            "expected the result event's 'analysis' field to be exactly "
            "the real AnalyzeResponse shape "
            "{'summary', 'explanation', 'chart_spec', 'follow_ups'}, "
            f"got: {result_data['analysis']!r}",
        )

    def test_result_event_analysis_follow_ups_is_a_nonempty_list_of_strings(self):
        events = _parse_sse_events(self.body_text)
        result_data = next(data for name, data in events if name == "result")
        follow_ups = result_data["analysis"]["follow_ups"]
        self.assertIsInstance(follow_ups, list)
        self.assertGreater(len(follow_ups), 0)
        for item in follow_ups:
            self.assertIsInstance(item, str)

    def test_body_contains_no_error_event(self):
        events = _parse_sse_events(self.body_text)
        error_events = [e for e in events if e[0] == "error"]
        self.assertEqual(
            error_events,
            [],
            f"did not expect an 'error' event for a real, answerable "
            f"question, got: {error_events!r}",
        )


class AskStreamFailurePathTests(unittest.TestCase):
    """Proves the stream endpoint's failure-signaling contract -- a
    pipeline exception surfaces as an `error` SSE event inside a 200
    response (the transport itself succeeded), not a crash and not an
    HTTP error status. Mirrors test_api_ask.py's
    AskEndpointFailurePathTests: a plain fake stands in for
    get_answer() instead of relying on a real double-LLM repair failure
    being reproducible through the NL-question-only HTTP interface. Per
    the wire-analyze-answer brief, this also covers an analyze_answer()
    failure inside get_answer(), since get_answer() is the one seam
    app/main.py calls for both steps."""

    def setUp(self):
        if _IMPORT_ERROR is not None:
            self.fail(
                f"could not import app.main.app: {_IMPORT_ERROR!r}"
            )

    def _stream_with_failing_get_answer(self):
        with patch("app.main.get_answer", side_effect=_fake_get_answer_that_fails):
            client = TestClient(app)
            with client.stream(
                "POST",
                "/api/ask/stream",
                json={"question": "irrelevant for this test"},
            ) as response:
                status_code = response.status_code
                body_text = "".join(response.iter_text())
        return status_code, body_text

    def test_pipeline_exception_still_returns_200_not_an_http_error(self):
        status_code, body_text = self._stream_with_failing_get_answer()
        self.assertEqual(
            status_code,
            200,
            "expected 200 even when get_answer() fails, per the brief's "
            "Outputs (the SSE stream itself succeeds; failure is signaled "
            f"by the event type), got {status_code}: {body_text}",
        )

    def test_pipeline_exception_is_not_a_crash_or_hung_stream(self):
        status_code, body_text = self._stream_with_failing_get_answer()
        self.assertIsInstance(body_text, str)
        self.assertGreater(
            len(body_text.strip()),
            0,
            "expected a non-empty SSE body instead of a hung/empty stream",
        )

    def test_body_contains_exactly_one_error_event(self):
        _, body_text = self._stream_with_failing_get_answer()
        events = _parse_sse_events(body_text)
        error_events = [e for e in events if e[0] == "error"]
        self.assertEqual(
            len(error_events),
            1,
            "expected exactly one 'error' SSE event when get_answer() "
            f"fails, got events: {events!r}",
        )

    def test_error_event_data_has_a_non_empty_detail_string(self):
        _, body_text = self._stream_with_failing_get_answer()
        events = _parse_sse_events(body_text)
        error_data = next(data for name, data in events if name == "error")
        self.assertIn(
            "detail",
            error_data,
            f"expected a 'detail' key in the error event's data, got: {error_data!r}",
        )
        self.assertIsInstance(error_data["detail"], str)
        self.assertGreater(
            len(error_data["detail"].strip()),
            0,
            f"expected a non-empty detail string, got: {error_data['detail']!r}",
        )

    def test_body_contains_no_result_event(self):
        _, body_text = self._stream_with_failing_get_answer()
        events = _parse_sse_events(body_text)
        result_events = [e for e in events if e[0] == "result"]
        self.assertEqual(
            result_events,
            [],
            f"did not expect a 'result' event when get_answer() fails, "
            f"got: {result_events!r}",
        )


if __name__ == "__main__":
    unittest.main()
