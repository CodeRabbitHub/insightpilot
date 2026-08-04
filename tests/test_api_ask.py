"""
Tests for the FastAPI /api/ask endpoint brief
(plans/briefs/2026-08-04-fastapi-ask-endpoint.md): a new `app/main.py`
wraps the existing, unchanged `app.pipeline.answer.get_answer(question)`
so it is reachable over HTTP via `POST /api/ask`.

Per the brief's Outputs: request `{"question": str}` -> `200
{"sql": str, "rows": [...]}` on success, `502 {"detail": str}` if
get_answer()'s repair loop also fails (a real HTTP error status, not an
uncaught 500 crash).

AskEndpointHappyPathTests makes one real call through the real pipeline
(no mocking the LLM/DB), using FastAPI's TestClient and
`app.pipeline.generate_sql.FIXED_QUESTION` -- this project's existing
canonical example question -- per the brief's explicit instruction that
these tests "make real calls through the real pipeline (no mocking the
LLM/DB)". Follows this repo's shared setUpClass convention
(test_answer_repair.py's AnswerWithRepairEndToEndTests): sync/describe run
once per class via _catalog_helpers/_describe_helpers, and the one
real, billed request is made once in setUpClass and shared across test
methods, not repeated per-test.

AskEndpointFailurePathTests proves the transport-level contract -- an
exception out of the pipeline call maps to 502, not a crash. The brief's
Outputs literally call for a "hand-crafted unrecoverable input that
fails both repair attempts". This is a documented, deliberate deviation
from that exact wording (approved at this slice's Gate 1 plan review),
not something the brief itself suggests: forcing a real double-LLM
repair failure through the NL-question-only HTTP interface can't be done
deterministically (unlike test_answer_repair.py, which can inject a
BROKEN_SQL string directly into _answer_with_repair() -- no such seam is
exposed over HTTP). So the "second repair attempt also fails" case is
proven the same way test_answer_repair.py's RetryOnceTests proves
propagation: with a plain fake standing in for get_answer(), patched at
`app.main.get_answer` (the one function app/main.py's handler calls),
instead of real I/O.

Test_empty_question_maps_to_502_via_the_real_pipeline below covers a
second, genuinely real and deterministic failure case with no mocking at
all: an empty question makes Voyage's embedding call reject the input
before generate_sql() ever reaches the repair loop, so it exercises a
real hand-crafted-input failure end to end, closing the gap the mocked
test alone leaves open.

Will fail honestly until app/main.py (and its FastAPI app instance)
exist -- no implementation file is created here.
"""
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


class AskEndpointHappyPathTests(unittest.TestCase):
    """Real question, real pipeline, real HTTP round-trip through
    FastAPI's TestClient -- no mocking of the LLM or DB, per the brief's
    explicit test-convention instruction."""

    @classmethod
    def setUpClass(cls):
        cls.sync_result = run_sync()
        cls.describe_result = run_describe()
        cls.response = None
        cls.request_error = None
        if (
            _IMPORT_ERROR is None
            and cls.sync_result.returncode == 0
            and cls.describe_result.returncode == 0
        ):
            try:
                client = TestClient(app)
                # One real, billed pipeline call (LLM + read-only DB
                # execute), shared across every test in this class.
                cls.response = client.post(
                    "/api/ask", json={"question": generate_sql.FIXED_QUESTION}
                )
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
                "POST /api/ask raised instead of returning a response: "
                f"{self.request_error!r}"
            )
        self.assertIsNotNone(
            self.response,
            "no response was captured -- see the other failures above",
        )

    def test_returns_200_for_the_fixed_question(self):
        self.assertEqual(
            self.response.status_code,
            200,
            f"expected 200 for a real, answerable question, got "
            f"{self.response.status_code}: {self.response.text}",
        )

    def test_response_body_has_exactly_the_sql_and_rows_keys(self):
        body = self.response.json()
        self.assertEqual(
            set(body.keys()),
            {"sql", "rows"},
            f"expected the success response body to be exactly "
            f"{{'sql', 'rows'}} per the brief's Outputs, got: {body!r}",
        )

    def test_response_sql_is_a_non_empty_string(self):
        body = self.response.json()
        self.assertIsInstance(body["sql"], str)
        self.assertGreater(
            len(body["sql"].strip()),
            0,
            f"expected a non-empty SQL string, got: {body['sql']!r}",
        )

    def test_response_rows_is_a_non_empty_list(self):
        body = self.response.json()
        self.assertIsInstance(body["rows"], list)
        self.assertGreater(
            len(body["rows"]),
            0,
            f"expected at least one real row back, got: {body['rows']!r}",
        )


class AskEndpointFailurePathTests(unittest.TestCase):
    """Proves the endpoint maps a pipeline exception to a real HTTP
    error status (502), not a crash -- the transport-level contract the
    brief requires, isolated from the LLM's own nondeterminism the same
    way RetryOnceTests isolates repair-loop propagation: a plain fake
    stands in for get_answer() instead of relying on a real
    double-failure being reproducible."""

    def setUp(self):
        if _IMPORT_ERROR is not None:
            self.fail(
                f"could not import app.main.app: {_IMPORT_ERROR!r}"
            )

    def test_pipeline_exception_maps_to_a_502_not_a_crash(self):
        with patch("app.main.get_answer", side_effect=_fake_get_answer_that_fails):
            client = TestClient(app)
            response = client.post(
                "/api/ask", json={"question": "irrelevant for this test"}
            )

        self.assertEqual(
            response.status_code,
            502,
            "expected a 502 when get_answer()'s repair loop fails, per "
            f"the brief's Outputs, got {response.status_code}: "
            f"{response.text}",
        )

    def test_502_response_body_has_a_detail_string(self):
        with patch("app.main.get_answer", side_effect=_fake_get_answer_that_fails):
            client = TestClient(app)
            response = client.post(
                "/api/ask", json={"question": "irrelevant for this test"}
            )

        body = response.json()
        self.assertIn(
            "detail",
            body,
            f"expected a 'detail' key in the 502 error body, got: {body!r}",
        )
        self.assertIsInstance(body["detail"], str)


class AskEndpointRealFailureInputTests(unittest.TestCase):
    """A genuinely real, unmocked, deterministic failure case: an empty
    question makes Voyage's embedding call (inside generate_sql(), before
    the repair loop even runs) reject the input every time, closing the
    gap AskEndpointFailurePathTests' mocked scenario leaves open -- this
    is the "hand-crafted unrecoverable input" the brief's Outputs asks
    for, exercised through the real pipeline, no mocking of the LLM/DB."""

    def setUp(self):
        if _IMPORT_ERROR is not None:
            self.fail(
                f"could not import app.main.app: {_IMPORT_ERROR!r}"
            )

    def test_empty_question_maps_to_502_via_the_real_pipeline(self):
        client = TestClient(app)
        response = client.post("/api/ask", json={"question": ""})

        self.assertEqual(
            response.status_code,
            502,
            "expected a real 502 (not a crash) when the real pipeline "
            f"rejects an empty question, got {response.status_code}: "
            f"{response.text}",
        )
        body = response.json()
        self.assertIsInstance(body.get("detail"), str)
        self.assertGreater(len(body["detail"]), 0)


if __name__ == "__main__":
    unittest.main()
