"""
Tests for the conversations-read-endpoints brief
(plans/briefs/2026-08-05-conversations-read-endpoints.md): two new
read-only routes to be added to `app/main.py` --
`GET /api/conversations` (every conversation, newest first, as
`[{"id", "title", "created_at"}, ...]`) and `GET /api/conversations/{id}`
(one conversation's detail plus its messages in chronological order, as
`{"id", "title", "created_at", "messages": [{"id", "role",
"content_json", "created_at"}, ...]}`, 404 on an unknown id).

This is written before app/main.py grows these two routes -- it will
fail to import/collect until that implementation lands, which is
expected and correct for tests written before implementation. The two
existing `POST` routes (`POST /api/conversations`,
`POST /api/conversations/{id}/messages`) and their own tests in
tests/test_api_conversations.py are reused here only as fixture-creation
calls; neither that file nor app/main.py's existing routes are modified.

ConversationDetailTests makes one real `POST /api/conversations` call
plus one real `POST /api/conversations/{id}/messages` call through the
real pipeline (no mocking the LLM/DB), using
`app.pipeline.generate_sql.FIXED_QUESTION` -- this project's existing
canonical example question -- following this repo's shared setUpClass
convention (test_api_ask_stream.py, test_api_conversations.py):
sync/describe run once via `_catalog_helpers`/`_describe_helpers`, and
the one real, billed request is made once in setUpClass and shared
across test methods. It then asserts `GET /api/conversations/{id}`
exactly -- shape, chronological order, and content -- cross-checked
against a direct database read via `async_session_factory`
(test_api_ask_persistence.py's async-helper-function-invoked-via-
asyncio.run() pattern), scoped to the exact conversation_id this test's
own calls created -- since this test owns that id's data completely, an
exact assertion (not a membership check) is appropriate here, per the
brief.

Per the wire-analyze-answer brief
(plans/briefs/2026-08-05-wire-analyze-answer.md), the persisted
assistant message's `content_json` gains an `"analysis"` key alongside
`"sql"`/`"rows"` (via `_persist_message_pair()`'s existing
`jsonable_encoder(response)` call on the whole `ConversationMessageResult`,
which now has an `analysis` field). The key-set assertion below is
updated to that new shape.

ConversationListMembershipTests makes its own cheap `POST
/api/conversations` call (no LLM) and asserts the resulting id is a
member of `GET /api/conversations`'s list -- a membership check, not an
exact count or length, per the brief's explicit no-slop category-5
instruction, since other conversations may exist in the live dev DB at
any time and the stop_verify hook may run this suite concurrently
against it.

ConversationListOrderingTests creates two more cheap conversations back
to back and asserts the second (newer) one appears before the first
(older) one in `GET /api/conversations`'s list -- proving the
newest-first ordering the brief promises without an exact-count or
exact-position assertion, so it stays robust to other rows anywhere else
in that list.

ConversationDetailWithNoMessagesTests makes its own cheap `POST
/api/conversations` call (no LLM, no messages posted) and asserts `GET
/api/conversations/{id}` still returns 200 with an empty `messages`
list -- the real conversation-exists-but-has-no-messages state a client
sees right after creating a conversation and before its first message.

UnknownConversationIdDetailTests uses the same large fixed sentinel
conversation id (999_999_999) as test_api_conversations.py, rather than
"max existing id + 1", to avoid a race against conversations
concurrently created by another instance of this suite, and asserts
`GET /api/conversations/{id}` 404s for it.
"""
import asyncio
import unittest

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


class ConversationDetailTests(unittest.TestCase):
    """GET /api/conversations/{id} for a real conversation that has a
    real, persisted user/assistant message pair must return that
    conversation's id, a null title, and both messages in chronological
    (oldest-first) order with exactly the shape and content the brief
    promises."""

    @classmethod
    def setUpClass(cls):
        cls.sync_result = run_sync()
        cls.describe_result = run_describe()
        cls.conversation_id = None
        cls.stream_status_code = None
        cls.stream_body_text = None
        cls.request_error = None
        cls.db_messages = []
        cls.lookup_error = None
        if (
            _IMPORT_ERROR is None
            and cls.sync_result.returncode == 0
            and cls.describe_result.returncode == 0
        ):
            try:
                client = TestClient(app)
                create_response = client.post("/api/conversations")
                if create_response.status_code == 200:
                    cls.conversation_id = create_response.json()["id"]
                    with client.stream(
                        "POST",
                        f"/api/conversations/{cls.conversation_id}/messages",
                        json={"question": generate_sql.FIXED_QUESTION},
                    ) as response:
                        cls.stream_status_code = response.status_code
                        cls.stream_body_text = "".join(response.iter_text())
            except Exception as exc:  # noqa: BLE001 -- captured, not swallowed
                cls.request_error = exc

            if cls.stream_status_code == 200 and cls.stream_body_text is not None:
                try:
                    cls.db_messages = asyncio.run(
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
                "the conversation-create or message-post fixture call "
                f"raised instead of completing: {self.request_error!r}"
            )
        self.assertIsNotNone(
            self.conversation_id,
            "no conversation_id was captured in setUpClass -- see the "
            "other failures above",
        )
        self.assertEqual(
            self.stream_status_code,
            200,
            "expected 200 from the fixture's POST "
            f"/api/conversations/{{id}}/messages call, got "
            f"{self.stream_status_code}: {self.stream_body_text}",
        )
        if self.lookup_error is not None:
            self.fail(
                f"querying messages for conversation_id={self.conversation_id} "
                f"raised: {self.lookup_error!r}"
            )
        self.assertEqual(
            len(self.db_messages),
            2,
            "expected exactly a persisted user/assistant message pair "
            f"for conversation_id={self.conversation_id} before these "
            f"detail-endpoint tests run, got {len(self.db_messages)}: "
            f"{[(m.id, m.role) for m in self.db_messages]!r}",
        )
        self.client = TestClient(app)

    def _get_detail(self):
        return self.client.get(f"/api/conversations/{self.conversation_id}")

    def test_returns_200_for_a_real_conversation(self):
        response = self._get_detail()
        self.assertEqual(
            response.status_code,
            200,
            "expected 200 for a real conversation id, got "
            f"{response.status_code}: {response.text}",
        )

    def test_body_has_exactly_the_expected_top_level_keys(self):
        body = self._get_detail().json()
        self.assertEqual(
            set(body.keys()),
            {"id", "title", "created_at", "messages"},
            "expected exactly {'id', 'title', 'created_at', 'messages'} "
            f"per the brief's Outputs, got: {body!r}",
        )

    def test_id_matches_the_requested_conversation(self):
        body = self._get_detail().json()
        self.assertEqual(body["id"], self.conversation_id)

    def test_title_is_null(self):
        body = self._get_detail().json()
        self.assertIsNone(
            body["title"],
            "expected title to be exactly null -- no endpoint sets one "
            f"yet -- got: {body['title']!r}",
        )

    def test_created_at_is_a_non_empty_string(self):
        body = self._get_detail().json()
        self.assertIsInstance(body["created_at"], str)
        self.assertGreater(
            len(body["created_at"].strip()),
            0,
            f"expected a non-empty created_at string, got: {body['created_at']!r}",
        )

    def test_messages_list_has_exactly_two_entries(self):
        body = self._get_detail().json()
        self.assertEqual(
            len(body["messages"]),
            2,
            "expected exactly the persisted user/assistant pair for "
            f"conversation_id={self.conversation_id}, got: "
            f"{body['messages']!r}",
        )

    def test_messages_are_in_chronological_order_user_then_assistant(self):
        body = self._get_detail().json()
        messages = body["messages"]
        self.assertEqual(
            messages[0]["role"],
            "user",
            f"expected the first (oldest) message to be the user's, got: {messages!r}",
        )
        self.assertEqual(
            messages[1]["role"],
            "assistant",
            f"expected the second message to be the assistant's, got: {messages!r}",
        )
        self.assertLess(
            messages[0]["id"],
            messages[1]["id"],
            "expected the user message (persisted first) to have a "
            f"lower id than the assistant reply, got: {messages!r}",
        )

    def test_each_message_has_exactly_the_expected_keys(self):
        body = self._get_detail().json()
        for message in body["messages"]:
            self.assertEqual(
                set(message.keys()),
                {"id", "role", "content_json", "created_at"},
                "expected exactly {'id', 'role', 'content_json', 'created_at'} "
                f"per message, got: {message!r}",
            )

    def test_message_ids_match_the_directly_persisted_rows(self):
        body = self._get_detail().json()
        api_ids = [m["id"] for m in body["messages"]]
        db_ids = [m.id for m in self.db_messages]
        self.assertEqual(
            api_ids,
            db_ids,
            "expected the detail endpoint's message ids and order to "
            f"match the directly-persisted rows exactly, got api={api_ids!r} "
            f"vs db={db_ids!r}",
        )

    def test_first_messages_content_json_is_exactly_the_user_question(self):
        body = self._get_detail().json()
        self.assertEqual(
            body["messages"][0]["content_json"],
            {"question": generate_sql.FIXED_QUESTION},
            "expected the first message's content_json to be exactly "
            f"{{'question': {generate_sql.FIXED_QUESTION!r}}}, got: "
            f"{body['messages'][0]['content_json']!r}",
        )

    def test_second_messages_content_json_matches_the_persisted_assistant_row(self):
        body = self._get_detail().json()
        assistant_db_row = self.db_messages[1]
        self.assertEqual(
            body["messages"][1]["content_json"],
            assistant_db_row.content_json,
            "expected content_json to be returned exactly as persisted, "
            f"no reshaping, got api={body['messages'][1]['content_json']!r} "
            f"vs db={assistant_db_row.content_json!r}",
        )

    def test_second_messages_content_json_has_exactly_sql_rows_and_analysis_keys(
        self,
    ):
        body = self._get_detail().json()
        self.assertEqual(
            set(body["messages"][1]["content_json"].keys()),
            {"sql", "rows", "analysis"},
            "expected the persisted assistant content_json to be exactly "
            "{'sql', 'rows', 'analysis'} per the wire-analyze-answer "
            f"brief's Outputs, got: {body['messages'][1]['content_json']!r}",
        )

    def test_second_messages_content_json_analysis_has_the_analyze_response_shape(
        self,
    ):
        body = self._get_detail().json()
        analysis = body["messages"][1]["content_json"]["analysis"]
        self.assertIsInstance(analysis, dict)
        self.assertEqual(
            set(analysis.keys()),
            {"summary", "explanation", "chart_spec", "follow_ups"},
            "expected the persisted assistant content_json's 'analysis' "
            "value to be exactly the real AnalyzeResponse shape "
            "{'summary', 'explanation', 'chart_spec', 'follow_ups'}, "
            f"got: {analysis!r}",
        )
        self.assertGreater(len(analysis["follow_ups"]), 0)

    def test_each_messages_created_at_is_a_non_empty_string(self):
        body = self._get_detail().json()
        for message in body["messages"]:
            self.assertIsInstance(message["created_at"], str)
            self.assertGreater(
                len(message["created_at"].strip()),
                0,
                f"expected a non-empty created_at string, got: {message!r}",
            )


class ConversationListMembershipTests(unittest.TestCase):
    """GET /api/conversations must include a conversation this test
    itself created via POST /api/conversations, identified by id --
    checked as membership, never an exact count, since other
    conversations may exist in the live dev DB at any time (brief's
    no-slop category-5 instruction)."""

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
        self.client = TestClient(app)

    def test_list_endpoint_returns_200(self):
        response = self.client.get("/api/conversations")
        self.assertEqual(
            response.status_code,
            200,
            f"expected 200, got {response.status_code}: {response.text}",
        )

    def test_list_response_body_is_a_list(self):
        response = self.client.get("/api/conversations")
        self.assertIsInstance(
            response.json(),
            list,
            f"expected a JSON array body, got: {response.json()!r}",
        )

    def test_created_conversation_is_a_member_of_the_list_by_id(self):
        body = self.client.get("/api/conversations").json()
        ids = [item["id"] for item in body]
        self.assertIn(
            self.conversation_id,
            ids,
            f"expected conversation_id={self.conversation_id} (created "
            "by this test's own POST /api/conversations call) to be "
            f"present in GET /api/conversations's list, got ids: {ids!r}",
        )

    def test_the_created_conversations_list_entry_has_exactly_the_expected_keys(self):
        body = self.client.get("/api/conversations").json()
        item = next(i for i in body if i["id"] == self.conversation_id)
        self.assertEqual(
            set(item.keys()),
            {"id", "title", "created_at"},
            "expected exactly {'id', 'title', 'created_at'} per list "
            f"entry, got: {item!r}",
        )

    def test_the_created_conversations_list_entry_has_a_null_title(self):
        body = self.client.get("/api/conversations").json()
        item = next(i for i in body if i["id"] == self.conversation_id)
        self.assertIsNone(
            item["title"],
            f"expected title to be null, got: {item['title']!r}",
        )

    def test_the_created_conversations_list_entry_has_a_non_empty_created_at(self):
        body = self.client.get("/api/conversations").json()
        item = next(i for i in body if i["id"] == self.conversation_id)
        self.assertIsInstance(item["created_at"], str)
        self.assertGreater(
            len(item["created_at"].strip()),
            0,
            f"expected a non-empty created_at string, got: {item['created_at']!r}",
        )


class ConversationListOrderingTests(unittest.TestCase):
    """GET /api/conversations must list conversations newest-first: a
    conversation created after another must appear before it in the
    list. Checked only via the relative order of these two known ids
    (never a global position or count), so it stays robust to any other
    rows the concurrently-running stop_verify hook may have inserted
    elsewhere in the same live table."""

    @classmethod
    def setUpClass(cls):
        cls.older_id = None
        cls.newer_id = None
        cls.create_error = None
        if _IMPORT_ERROR is None:
            try:
                client = TestClient(app)
                older_response = client.post("/api/conversations")
                if older_response.status_code == 200:
                    cls.older_id = older_response.json()["id"]
                newer_response = client.post("/api/conversations")
                if newer_response.status_code == 200:
                    cls.newer_id = newer_response.json()["id"]
            except Exception as exc:  # noqa: BLE001 -- captured, not swallowed
                cls.create_error = exc

    @classmethod
    def tearDownClass(cls):
        if cls.older_id is not None:
            asyncio.run(_delete_conversation_and_its_messages(cls.older_id))
        if cls.newer_id is not None:
            asyncio.run(_delete_conversation_and_its_messages(cls.newer_id))

    def setUp(self):
        if _IMPORT_ERROR is not None:
            self.fail(f"could not import required modules: {_IMPORT_ERROR!r}")
        if self.create_error is not None:
            self.fail(
                f"POST /api/conversations raised instead of completing: "
                f"{self.create_error!r}"
            )
        self.assertIsNotNone(
            self.older_id,
            "no older_id was captured -- the first POST /api/conversations "
            "call must have failed in setUpClass",
        )
        self.assertIsNotNone(
            self.newer_id,
            "no newer_id was captured -- the second POST /api/conversations "
            "call must have failed in setUpClass",
        )
        self.client = TestClient(app)

    def test_the_more_recently_created_conversation_appears_before_the_older_one(self):
        body = self.client.get("/api/conversations").json()
        ids = [item["id"] for item in body]
        self.assertIn(self.older_id, ids)
        self.assertIn(self.newer_id, ids)
        newer_index = ids.index(self.newer_id)
        older_index = ids.index(self.older_id)
        self.assertLess(
            newer_index,
            older_index,
            "expected GET /api/conversations to list conversations "
            f"newest-first, so conversation_id={self.newer_id} (created "
            f"after conversation_id={self.older_id}) should appear "
            f"earlier in the list, got ids in order: {ids!r}",
        )


class ConversationDetailWithNoMessagesTests(unittest.TestCase):
    """GET /api/conversations/{id} for a real conversation that has never
    had a message posted to it (the state immediately after `POST
    /api/conversations`, before any `POST .../messages` call) must still
    return 200 with an empty `messages` list -- not a 404 or an error --
    since the conversation itself exists."""

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
        self.client = TestClient(app)

    def _get_detail(self):
        return self.client.get(f"/api/conversations/{self.conversation_id}")

    def test_returns_200_not_404_for_a_real_conversation_with_no_messages(self):
        response = self._get_detail()
        self.assertEqual(
            response.status_code,
            200,
            "expected 200 for a real conversation with zero messages, got "
            f"{response.status_code}: {response.text}",
        )

    def test_messages_is_an_empty_list(self):
        body = self._get_detail().json()
        self.assertEqual(
            body["messages"],
            [],
            f"expected an empty messages list, got: {body['messages']!r}",
        )


class UnknownConversationIdDetailTests(unittest.TestCase):
    """GET /api/conversations/{id} for an id that does not refer to any
    real conversation must 404. Uses a large fixed sentinel id
    (999_999_999) rather than "max existing id + 1", matching
    test_api_conversations.py's convention, to avoid a race against
    conversations concurrently created by another instance of this
    suite."""

    def setUp(self):
        if _IMPORT_ERROR is not None:
            self.fail(f"could not import required modules: {_IMPORT_ERROR!r}")
        self.client = TestClient(app)

    def test_returns_404_for_the_sentinel_id(self):
        response = self.client.get(f"/api/conversations/{UNKNOWN_CONVERSATION_ID}")
        self.assertEqual(
            response.status_code,
            404,
            "expected 404 for an unknown conversation id, got "
            f"{response.status_code}: {response.text}",
        )


if __name__ == "__main__":
    unittest.main()
