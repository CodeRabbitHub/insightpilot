"""
Tests for the wire-persistence-into-ask-endpoints brief
(plans/briefs/2026-08-04-wire-persistence-into-ask-endpoints.md): each
successful `POST /api/ask` or `POST /api/ask/stream` request must persist
one new `app.Conversation`, a `user`-role `app.Message` holding the
question, and an `assistant`-role `app.Message` holding the same
`{"sql", "rows"}` shape returned to the client -- via
`app.db.session.async_session_factory` (the prior slice's pool), never
through `execute_sql()`'s read-only asyncpg pool. On any `get_answer()`
failure, nothing is persisted.

AskPersistenceHappyPathTests / AskStreamPersistenceHappyPathTests make one
real HTTP call through the real pipeline (no mocking the LLM/DB), using
`app.pipeline.generate_sql.FIXED_QUESTION` and this repo's shared
setUpClass convention (test_api_ask.py / test_api_ask_stream.py):
sync/describe run once via _catalog_helpers/_describe_helpers, and the
one real, billed request is made once in setUpClass.

Per the brief's explicit concurrency-safety instruction (the stop_verify
hook may run this suite concurrently with a manual run against the same
real dev DB), the happy-path checks below do NOT snapshot a max-id/count
before the call and diff afterwards. Instead, after the real call
completes, they identify "the exchange this call created" by querying the
single newest conversation (`ORDER BY id DESC LIMIT 1`) and its messages,
via `async_session_factory`/`asyncio.run()` called from these sync test
methods (mirroring test_app_db.py's async-helper-function pattern, since
unittest.TestCase methods here are not async).

AskPersistenceFailurePathTests / AskStreamPersistenceFailurePathTests
mirror the existing failure-path convention (a plain fake patched at
`app.main.get_answer`), but instead of asserting "no new conversation
exists" (which a concurrently-running happy-path test would trip), they
use a distinctive question string unique to this test run (a fresh
`uuid.uuid4()` per class, not a shared literal like "irrelevant for this
test") and assert no message anywhere has that exact `content_json` --
scoped to the exchange this specific failed call would have created.

Every happy-path test class deletes the messages then the conversation it
found in tearDownClass, mirroring test_app_db.py's cleanup pattern, so
repeat runs don't accumulate garbage in the real dev Postgres instance.

Written before app/main.py's persistence wiring existed, so these
happy-path checks failed honestly against the then-unmodified endpoints;
they now assert against that same wiring once it landed alongside this
file.
"""
import asyncio
import json
import unittest
import uuid
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

try:
    from sqlalchemy import select

    from app.db.models import Conversation, Message
    from app.db.session import async_session_factory
except Exception as exc:  # noqa: BLE001 -- captured so setUpClass can report it
    select = None
    Conversation = None
    Message = None
    async_session_factory = None
    if _IMPORT_ERROR is None:
        _IMPORT_ERROR = exc


async def _fake_get_answer_that_fails(question):
    raise RuntimeError("simulated repair-loop failure: both attempts failed")


def _parse_sse_events(body_text):
    """Hand-rolled SSE parser, duplicated from test_api_ask_stream.py's
    helper of the same name per this repo's existing per-file duplication
    convention (each stream test file owns its own copy)."""
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


async def _fetch_newest_conversation_with_messages():
    """The single newest conversation (by id) and its messages, ordered by
    id -- the concurrency-safe way to identify "the exchange this call
    created" per the brief, instead of snapshotting a count/max-id before
    the call and diffing afterwards."""
    async with async_session_factory() as session:
        conv_result = await session.execute(
            select(Conversation).order_by(Conversation.id.desc()).limit(1)
        )
        conversation = conv_result.scalars().first()
        if conversation is None:
            return None, []
        msg_result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.id)
        )
        messages = list(msg_result.scalars().all())
        return conversation, messages


async def _delete_conversation_and_its_messages(conversation_id):
    async with async_session_factory() as session:
        msg_result = await session.execute(
            select(Message).where(Message.conversation_id == conversation_id)
        )
        for message in msg_result.scalars().all():
            await session.delete(message)
        conversation = await session.get(Conversation, conversation_id)
        if conversation is not None:
            await session.delete(conversation)
        await session.commit()


async def _any_message_with_content_json(content_json):
    async with async_session_factory() as session:
        result = await session.execute(
            select(Message).where(Message.content_json == content_json)
        )
        return result.scalars().first() is not None


class AskPersistenceHappyPathTests(unittest.TestCase):
    """A real POST /api/ask call must persist a Conversation plus a
    user Message (the question) and an assistant Message (the response
    body), found via the newest-conversation lookup."""

    @classmethod
    def setUpClass(cls):
        cls.sync_result = run_sync()
        cls.describe_result = run_describe()
        cls.response = None
        cls.request_error = None
        cls.conversation = None
        cls.messages = []
        cls.lookup_error = None
        if (
            _IMPORT_ERROR is None
            and cls.sync_result.returncode == 0
            and cls.describe_result.returncode == 0
        ):
            try:
                client = TestClient(app)
                cls.response = client.post(
                    "/api/ask", json={"question": generate_sql.FIXED_QUESTION}
                )
            except Exception as exc:  # noqa: BLE001 -- captured, not swallowed
                cls.request_error = exc

            if cls.response is not None and cls.response.status_code == 200:
                try:
                    cls.conversation, cls.messages = asyncio.run(
                        _fetch_newest_conversation_with_messages()
                    )
                except Exception as exc:  # noqa: BLE001 -- captured, not swallowed
                    cls.lookup_error = exc

    @classmethod
    def tearDownClass(cls):
        if cls.conversation is not None:
            asyncio.run(_delete_conversation_and_its_messages(cls.conversation.id))

    def setUp(self):
        if _IMPORT_ERROR is not None:
            self.fail(f"could not import required modules: {_IMPORT_ERROR!r}")
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
        self.assertEqual(
            self.response.status_code,
            200,
            "expected 200 for the fixed, answerable question, got "
            f"{self.response.status_code}: {self.response.text}",
        )
        if self.lookup_error is not None:
            self.fail(
                "querying the newest conversation/messages raised: "
                f"{self.lookup_error!r}"
            )

    def test_a_new_conversation_was_persisted(self):
        self.assertIsNotNone(
            self.conversation,
            "expected a Conversation row to exist after a successful "
            "POST /api/ask, but the newest-conversation query found none",
        )

    def test_exactly_two_messages_belong_to_that_conversation(self):
        self.assertEqual(
            len(self.messages),
            2,
            "expected exactly one user message and one assistant message "
            f"for the newest conversation, got {len(self.messages)}: "
            f"{[(m.role, m.content_json) for m in self.messages]!r}",
        )

    def test_message_roles_are_user_then_assistant_in_id_order(self):
        self.assertEqual(
            [m.role for m in self.messages],
            ["user", "assistant"],
            "expected the two messages, ordered by id, to be roles "
            f"['user', 'assistant'], got: {[m.role for m in self.messages]!r}",
        )

    def test_user_message_content_json_holds_the_question(self):
        user_message = self.messages[0]
        self.assertEqual(
            user_message.content_json,
            {"question": generate_sql.FIXED_QUESTION},
            "expected the user message's content_json to be exactly "
            f"{{'question': {generate_sql.FIXED_QUESTION!r}}}, got: "
            f"{user_message.content_json!r}",
        )

    def test_assistant_message_content_json_matches_the_http_response_body(self):
        assistant_message = self.messages[1]
        self.assertEqual(
            assistant_message.content_json,
            self.response.json(),
            "expected the assistant message's content_json to match the "
            f"HTTP response body {self.response.json()!r} exactly, got: "
            f"{assistant_message.content_json!r}",
        )


class AskStreamPersistenceHappyPathTests(unittest.TestCase):
    """A real POST /api/ask/stream call must persist a Conversation plus
    a user Message (the question) and an assistant Message (the SSE
    result event's data), found via the newest-conversation lookup."""

    @classmethod
    def setUpClass(cls):
        cls.sync_result = run_sync()
        cls.describe_result = run_describe()
        cls.status_code = None
        cls.body_text = None
        cls.request_error = None
        cls.conversation = None
        cls.messages = []
        cls.lookup_error = None
        if (
            _IMPORT_ERROR is None
            and cls.sync_result.returncode == 0
            and cls.describe_result.returncode == 0
        ):
            try:
                client = TestClient(app)
                with client.stream(
                    "POST",
                    "/api/ask/stream",
                    json={"question": generate_sql.FIXED_QUESTION},
                ) as response:
                    cls.status_code = response.status_code
                    cls.body_text = "".join(response.iter_text())
            except Exception as exc:  # noqa: BLE001 -- captured, not swallowed
                cls.request_error = exc

            if cls.status_code == 200 and cls.body_text is not None:
                try:
                    cls.conversation, cls.messages = asyncio.run(
                        _fetch_newest_conversation_with_messages()
                    )
                except Exception as exc:  # noqa: BLE001 -- captured, not swallowed
                    cls.lookup_error = exc

    @classmethod
    def tearDownClass(cls):
        if cls.conversation is not None:
            asyncio.run(_delete_conversation_and_its_messages(cls.conversation.id))

    def setUp(self):
        if _IMPORT_ERROR is not None:
            self.fail(f"could not import required modules: {_IMPORT_ERROR!r}")
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
        self.assertEqual(
            self.status_code,
            200,
            "expected 200 for the fixed, answerable question over SSE, "
            f"got {self.status_code}: {self.body_text}",
        )
        events = _parse_sse_events(self.body_text)
        result_events = [e for e in events if e[0] == "result"]
        self.assertEqual(
            len(result_events),
            1,
            f"expected exactly one 'result' SSE event, got: {events!r}",
        )
        if self.lookup_error is not None:
            self.fail(
                "querying the newest conversation/messages raised: "
                f"{self.lookup_error!r}"
            )

    def _result_event_data(self):
        events = _parse_sse_events(self.body_text)
        return next(data for name, data in events if name == "result")

    def test_a_new_conversation_was_persisted(self):
        self.assertIsNotNone(
            self.conversation,
            "expected a Conversation row to exist after a successful "
            "POST /api/ask/stream, but the newest-conversation query "
            "found none",
        )

    def test_exactly_two_messages_belong_to_that_conversation(self):
        self.assertEqual(
            len(self.messages),
            2,
            "expected exactly one user message and one assistant message "
            f"for the newest conversation, got {len(self.messages)}: "
            f"{[(m.role, m.content_json) for m in self.messages]!r}",
        )

    def test_message_roles_are_user_then_assistant_in_id_order(self):
        self.assertEqual(
            [m.role for m in self.messages],
            ["user", "assistant"],
            "expected the two messages, ordered by id, to be roles "
            f"['user', 'assistant'], got: {[m.role for m in self.messages]!r}",
        )

    def test_user_message_content_json_holds_the_question(self):
        user_message = self.messages[0]
        self.assertEqual(
            user_message.content_json,
            {"question": generate_sql.FIXED_QUESTION},
            "expected the user message's content_json to be exactly "
            f"{{'question': {generate_sql.FIXED_QUESTION!r}}}, got: "
            f"{user_message.content_json!r}",
        )

    def test_assistant_message_content_json_matches_the_sse_result_event(self):
        assistant_message = self.messages[1]
        result_data = self._result_event_data()
        self.assertEqual(
            assistant_message.content_json,
            result_data,
            "expected the assistant message's content_json to match the "
            f"SSE 'result' event's data {result_data!r} exactly, got: "
            f"{assistant_message.content_json!r}",
        )


class AskPersistenceFailurePathTests(unittest.TestCase):
    """A failed POST /api/ask call (get_answer() raises) must persist
    nothing. Uses a distinctive, per-class-unique question so the check
    is scoped to the exchange this specific call would have created,
    not "no new conversation exists at all" -- which a concurrently
    running happy-path test would trip."""

    DISTINCT_QUESTION = f"persistence-failure-probe-ask-{uuid.uuid4()}"

    def setUp(self):
        if _IMPORT_ERROR is not None:
            self.fail(f"could not import required modules: {_IMPORT_ERROR!r}")

    def test_failed_request_returns_502(self):
        with patch("app.main.get_answer", side_effect=_fake_get_answer_that_fails):
            client = TestClient(app)
            response = client.post(
                "/api/ask", json={"question": self.DISTINCT_QUESTION}
            )
        self.assertEqual(
            response.status_code,
            502,
            "expected a 502 when get_answer() fails, got "
            f"{response.status_code}: {response.text}",
        )

    def test_failed_request_persists_no_message_with_its_question(self):
        with patch("app.main.get_answer", side_effect=_fake_get_answer_that_fails):
            client = TestClient(app)
            response = client.post(
                "/api/ask", json={"question": self.DISTINCT_QUESTION}
            )
        self.assertEqual(response.status_code, 502)

        exists = asyncio.run(
            _any_message_with_content_json({"question": self.DISTINCT_QUESTION})
        )
        self.assertFalse(
            exists,
            "expected no message anywhere to hold this test's distinctive "
            f"question ({self.DISTINCT_QUESTION!r}) after a failed "
            "get_answer() call, since only the success path should persist",
        )


class AskStreamPersistenceFailurePathTests(unittest.TestCase):
    """A failed POST /api/ask/stream call (get_answer() raises, surfacing
    as an 'error' SSE event) must persist nothing. Mirrors
    AskPersistenceFailurePathTests' distinctive-question, scoped-absence
    check."""

    DISTINCT_QUESTION = f"persistence-failure-probe-ask-stream-{uuid.uuid4()}"

    def setUp(self):
        if _IMPORT_ERROR is not None:
            self.fail(f"could not import required modules: {_IMPORT_ERROR!r}")

    def _stream_with_failing_get_answer(self):
        with patch("app.main.get_answer", side_effect=_fake_get_answer_that_fails):
            client = TestClient(app)
            with client.stream(
                "POST",
                "/api/ask/stream",
                json={"question": self.DISTINCT_QUESTION},
            ) as response:
                status_code = response.status_code
                body_text = "".join(response.iter_text())
        return status_code, body_text

    def test_failed_request_surfaces_as_an_error_event(self):
        status_code, body_text = self._stream_with_failing_get_answer()
        self.assertEqual(status_code, 200)
        events = _parse_sse_events(body_text)
        error_events = [e for e in events if e[0] == "error"]
        self.assertEqual(
            len(error_events),
            1,
            f"expected exactly one 'error' SSE event, got: {events!r}",
        )

    def test_failed_request_persists_no_message_with_its_question(self):
        status_code, body_text = self._stream_with_failing_get_answer()
        self.assertEqual(status_code, 200)
        events = _parse_sse_events(body_text)
        error_events = [e for e in events if e[0] == "error"]
        self.assertEqual(len(error_events), 1)

        exists = asyncio.run(
            _any_message_with_content_json({"question": self.DISTINCT_QUESTION})
        )
        self.assertFalse(
            exists,
            "expected no message anywhere to hold this test's distinctive "
            f"question ({self.DISTINCT_QUESTION!r}) after a failed "
            "get_answer() call, since only the success path should persist",
        )


if __name__ == "__main__":
    unittest.main()
