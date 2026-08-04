"""
Tests for the conversations-endpoints brief
(plans/briefs/2026-08-04-conversations-endpoints.md): a real, multi-turn
conversations surface on `app/main.py` --
`POST /api/conversations` (creates one empty `Conversation` row, returns
`{"id": int}`) and `POST /api/conversations/{id}/messages` (404s
immediately, with zero `get_answer()` calls and nothing persisted, if
`id` doesn't refer to a real conversation; otherwise runs the real
`get_answer()` pipeline, persists the `user`/`assistant` message pair
under that exact `conversation_id`, and streams the outcome as SSE,
where a successful `result` event's data is exactly
`{"conversation_id", "message_id", "sql", "rows"}`).

This is written before app/main.py grows these two routes -- it will
fail to import/collect until that implementation lands, which is
expected and correct for tests written before implementation.

ConversationMessageHappyPathTests makes one real `POST /api/conversations`
call plus one real `POST /api/conversations/{id}/messages` call through
the real pipeline (no mocking the LLM/DB), using
`app.pipeline.generate_sql.FIXED_QUESTION` -- this project's existing
canonical example question -- following this repo's shared setUpClass
convention (test_api_ask_stream.py): sync/describe run once via
`_catalog_helpers`/`_describe_helpers`, and the one real, billed request
is made once in setUpClass and shared across test methods. It parses the
raw SSE body with the same hand-rolled `_parse_sse_events` helper
duplicated from test_api_ask_stream.py (each stream test file in this
repo owns its own copy, per that file's convention), and asserts
directly against the database via `async_session_factory`
(test_api_ask_persistence.py's async-helper-function-invoked-via-
asyncio.run() pattern) -- but scoped to the exact `conversation_id` this
test's own calls created, never a newest-row lookup or a global count,
since the brief requires these assertions to survive the stop_verify
hook running this suite concurrently against the live dev DB.

UnknownConversationIdTests uses a large fixed sentinel conversation id
(999_999_999) rather than "max existing id + 1", per the brief's
explicit instruction, to avoid a race against concurrently created
conversations from another stop_verify run. It patches
`app.main.get_answer` with a fake that calls `self.fail(...)` if it is
ever invoked, proving the 404 fires with zero LLM calls -- mirroring
test_api_ask_stream.py's `patch("app.main.get_answer", ...)` import path.

ConversationMessageFailurePathTests mirrors test_api_ask_stream.py's
`_fake_get_answer_that_fails` exactly, patched onto a real conversation
created (cheaply, no LLM) once in setUpClass, and asserts the SSE
transport still returns 200 with exactly one `error` event and nothing
persisted under that real conversation id.
"""
import asyncio
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


UNKNOWN_CONVERSATION_ID = 999_999_999


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


async def _messages_for_conversation(conversation_id):
    """Messages belonging to exactly this conversation_id, ordered by id
    -- scoped so a concurrently running instance of this suite (the
    stop_verify hook may run it against the same live dev DB) never
    affects this assertion."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id)
        )
        return list(result.scalars().all())


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


class ConversationMessageHappyPathTests(unittest.TestCase):
    """A real POST /api/conversations call followed by a real
    POST /api/conversations/{id}/messages call through the real
    pipeline (no mocking the LLM/DB) must return a real conversation id,
    a real streamed answer scoped to that id, and persist exactly the
    user/assistant message pair under that same conversation_id."""

    @classmethod
    def setUpClass(cls):
        cls.sync_result = run_sync()
        cls.describe_result = run_describe()
        cls.create_response = None
        cls.conversation_id = None
        cls.status_code = None
        cls.body_text = None
        cls.request_error = None
        cls.messages = []
        cls.lookup_error = None
        if (
            _IMPORT_ERROR is None
            and cls.sync_result.returncode == 0
            and cls.describe_result.returncode == 0
        ):
            try:
                client = TestClient(app)
                cls.create_response = client.post("/api/conversations")
                if cls.create_response.status_code == 200:
                    cls.conversation_id = cls.create_response.json()["id"]
                    with client.stream(
                        "POST",
                        f"/api/conversations/{cls.conversation_id}/messages",
                        json={"question": generate_sql.FIXED_QUESTION},
                    ) as response:
                        cls.status_code = response.status_code
                        cls.body_text = "".join(response.iter_text())
            except Exception as exc:  # noqa: BLE001 -- captured, not swallowed
                cls.request_error = exc

            if cls.status_code == 200 and cls.body_text is not None:
                try:
                    cls.messages = asyncio.run(
                        _messages_for_conversation(cls.conversation_id)
                    )
                except Exception as exc:  # noqa: BLE001 -- captured, not swallowed
                    cls.lookup_error = exc

    @classmethod
    def tearDownClass(cls):
        if cls.conversation_id is not None:
            asyncio.run(_delete_conversation_and_its_messages(cls.conversation_id))

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
                "the conversation-create or message-post call raised "
                f"instead of completing: {self.request_error!r}"
            )
        self.assertIsNotNone(
            self.create_response,
            "no response was captured for POST /api/conversations -- see "
            "the other failures above",
        )
        self.assertEqual(
            self.create_response.status_code,
            200,
            "expected 200 for POST /api/conversations, got "
            f"{self.create_response.status_code}: {self.create_response.text}",
        )
        self.assertIsNotNone(
            self.body_text,
            "no streamed body was captured for POST "
            "/api/conversations/{id}/messages -- see the other failures above",
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
                f"querying messages for conversation_id={self.conversation_id} "
                f"raised: {self.lookup_error!r}"
            )

    def _result_event_data(self):
        events = _parse_sse_events(self.body_text)
        return next(data for name, data in events if name == "result")

    def test_creating_a_conversation_returns_an_int_id(self):
        self.assertIsInstance(
            self.conversation_id,
            int,
            f"expected POST /api/conversations to return an int id, got: "
            f"{self.create_response.json()!r}",
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

    def test_body_contains_no_error_event(self):
        events = _parse_sse_events(self.body_text)
        error_events = [e for e in events if e[0] == "error"]
        self.assertEqual(
            error_events,
            [],
            "did not expect an 'error' event for a real, answerable "
            f"question, got: {error_events!r}",
        )

    def test_result_event_data_has_exactly_the_expected_keys(self):
        result_data = self._result_event_data()
        self.assertEqual(
            set(result_data.keys()),
            {"conversation_id", "message_id", "sql", "rows"},
            "expected the result event's data to be exactly "
            "{'conversation_id', 'message_id', 'sql', 'rows'} per the "
            f"brief's Outputs, got: {result_data!r}",
        )

    def test_result_event_conversation_id_matches_the_created_conversation(self):
        result_data = self._result_event_data()
        self.assertEqual(
            result_data["conversation_id"],
            self.conversation_id,
            "expected the result event's conversation_id to match the "
            f"conversation this test created ({self.conversation_id!r}), "
            f"got: {result_data['conversation_id']!r}",
        )

    def test_result_event_message_id_is_an_int(self):
        result_data = self._result_event_data()
        self.assertIsInstance(
            result_data["message_id"],
            int,
            f"expected an int message_id, got: {result_data['message_id']!r}",
        )

    def test_result_event_sql_is_a_non_empty_string(self):
        result_data = self._result_event_data()
        self.assertIsInstance(result_data["sql"], str)
        self.assertGreater(
            len(result_data["sql"].strip()),
            0,
            f"expected a non-empty SQL string, got: {result_data['sql']!r}",
        )

    def test_result_event_rows_is_a_non_empty_list(self):
        result_data = self._result_event_data()
        self.assertIsInstance(result_data["rows"], list)
        self.assertGreater(
            len(result_data["rows"]),
            0,
            f"expected at least one real row back, got: {result_data['rows']!r}",
        )

    def test_exactly_two_messages_persisted_under_that_conversation_id(self):
        self.assertEqual(
            len(self.messages),
            2,
            "expected exactly one user message and one assistant message "
            f"for conversation_id={self.conversation_id}, got "
            f"{len(self.messages)}: "
            f"{[(m.role, m.content_json) for m in self.messages]!r}",
        )

    def test_first_message_is_the_user_question(self):
        user_message = self.messages[0]
        self.assertEqual(user_message.role, "user")
        self.assertEqual(
            user_message.content_json,
            {"question": generate_sql.FIXED_QUESTION},
            "expected the first message's content_json to be exactly "
            f"{{'question': {generate_sql.FIXED_QUESTION!r}}}, got: "
            f"{user_message.content_json!r}",
        )

    def test_second_message_is_the_assistant_reply_with_the_streamed_message_id(self):
        assistant_message = self.messages[1]
        result_data = self._result_event_data()
        self.assertEqual(assistant_message.role, "assistant")
        self.assertEqual(
            assistant_message.id,
            result_data["message_id"],
            "expected the second persisted message's id to equal the "
            f"SSE result event's message_id ({result_data['message_id']!r}), "
            f"got: {assistant_message.id!r}",
        )


class UnknownConversationIdTests(unittest.TestCase):
    """POST /api/conversations/{id}/messages against a conversation id
    that does not exist must 404 before ever calling get_answer(), and
    must persist nothing. Uses a large fixed sentinel id
    (999_999_999) rather than "max existing id + 1", per the brief, to
    avoid a race against conversations concurrently created by another
    instance of this suite."""

    def setUp(self):
        if _IMPORT_ERROR is not None:
            self.fail(f"could not import required modules: {_IMPORT_ERROR!r}")

    def _post_message_to_unknown_conversation(self):
        async def _fake_get_answer_that_must_not_be_called(question):
            self.fail(
                "get_answer() must not be called for an unknown "
                "conversation id -- the 404 check must happen first, "
                "with zero LLM calls"
            )

        with patch(
            "app.main.get_answer",
            side_effect=_fake_get_answer_that_must_not_be_called,
        ):
            client = TestClient(app)
            response = client.post(
                f"/api/conversations/{UNKNOWN_CONVERSATION_ID}/messages",
                json={"question": "irrelevant for this test"},
            )
        return response

    def test_returns_404(self):
        response = self._post_message_to_unknown_conversation()
        self.assertEqual(
            response.status_code,
            404,
            "expected 404 for an unknown conversation id, got "
            f"{response.status_code}: {response.text}",
        )

    def test_persists_no_messages_for_that_conversation_id(self):
        response = self._post_message_to_unknown_conversation()
        self.assertEqual(response.status_code, 404)

        messages = asyncio.run(
            _messages_for_conversation(UNKNOWN_CONVERSATION_ID)
        )
        self.assertEqual(
            messages,
            [],
            "expected zero messages for the unknown sentinel "
            f"conversation_id={UNKNOWN_CONVERSATION_ID}, got: "
            f"{[(m.id, m.role, m.content_json) for m in messages]!r}",
        )


class ConversationMessageFailurePathTests(unittest.TestCase):
    """A get_answer() failure against a real, existing conversation must
    still surface as an 'error' SSE event inside a 200 response (the SSE
    transport itself succeeded), and must persist nothing under that
    conversation's id."""

    @classmethod
    def setUpClass(cls):
        cls.conversation_id = None
        cls.create_error = None
        if _IMPORT_ERROR is None:
            try:
                client = TestClient(app)
                create_response = client.post("/api/conversations")
                if create_response.status_code == 200:
                    cls.conversation_id = create_response.json()["id"]
            except Exception as exc:  # noqa: BLE001 -- captured, not swallowed
                cls.create_error = exc

    @classmethod
    def tearDownClass(cls):
        if cls.conversation_id is not None:
            asyncio.run(_delete_conversation_and_its_messages(cls.conversation_id))

    def setUp(self):
        if _IMPORT_ERROR is not None:
            self.fail(f"could not import required modules: {_IMPORT_ERROR!r}")
        if self.create_error is not None:
            self.fail(
                f"POST /api/conversations raised instead of completing: "
                f"{self.create_error!r}"
            )
        self.assertIsNotNone(
            self.conversation_id,
            "no conversation_id was captured -- POST /api/conversations "
            "must have failed in setUpClass",
        )

    def _stream_with_failing_get_answer(self):
        with patch("app.main.get_answer", side_effect=_fake_get_answer_that_fails):
            client = TestClient(app)
            with client.stream(
                "POST",
                f"/api/conversations/{self.conversation_id}/messages",
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

    def test_failed_request_persists_no_messages_for_that_conversation(self):
        status_code, body_text = self._stream_with_failing_get_answer()
        self.assertEqual(status_code, 200)
        events = _parse_sse_events(body_text)
        error_events = [e for e in events if e[0] == "error"]
        self.assertEqual(len(error_events), 1)

        messages = asyncio.run(_messages_for_conversation(self.conversation_id))
        self.assertEqual(
            messages,
            [],
            "expected zero messages for conversation_id="
            f"{self.conversation_id} after a failed get_answer() call, "
            f"got: {[(m.id, m.role, m.content_json) for m in messages]!r}",
        )


if __name__ == "__main__":
    unittest.main()
