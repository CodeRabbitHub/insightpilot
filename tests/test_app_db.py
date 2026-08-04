"""
Real round-trip tests for the app-schema persistence foundation brief
(plans/briefs/2026-08-04-app-schema-persistence.md): a SQLAlchemy 2.0
async engine/session factory at `app/db/session.py`, authenticated as
POSTGRES_USER (insightpilot_owner) against the `app` schema, plus ORM
models at `app/db/models.py` -- `Conversation` (id, title, created_at)
and `Message` (id, conversation_id FK, role, content_json, created_at).

The brief leaves the engine/session factory's exact object names to the
implementation's discretion ("app/db/session.py (or equivalent)" in its
Outputs) -- since this suite is written before that implementation
exists, it fixes two names for the implementation to satisfy:
`app.db.session.engine` (the async
Engine) and `app.db.session.async_session_factory` (an
`async_sessionmaker` bound to it). Both are exercised for real, no
mocking of the DB, per this project's established convention
(tests/test_glossary_verify_embed.py, tests/test_execute_sql_ro_role.py).

Assumes `alembic upgrade head` (or the project's equivalent migration
run) has already created the `app` schema, `app.conversations`, and
`app.messages` tables against the real dev Postgres instance before this
suite runs -- the brief's done-check runs that command separately from
this file.

Every test that inserts rows deletes them again in a `finally` block
(mirroring test_glossary_verify_embed.py's cleanup pattern) so repeat
runs don't accumulate garbage in the real dev Postgres instance, and one
test asserts that cleanup deletion is actually effective.

Will fail honestly (ImportError) until app/db/session.py and
app/db/models.py exist.
"""
import os
import unittest

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from _pg_helpers import conn_params  # noqa: F401 -- loads .env / defaults

from app.db.models import Conversation, Message
from app.db.session import async_session_factory, engine

_NONEXISTENT_CONVERSATION_ID = -1


async def _create_conversation_and_message(title, role, content_json):
    async with async_session_factory() as session:
        conversation = Conversation(title=title)
        session.add(conversation)
        await session.flush()
        message = Message(
            conversation_id=conversation.id,
            role=role,
            content_json=content_json,
        )
        session.add(message)
        await session.commit()
        return conversation.id, message.id


async def _delete_conversation_and_message(conversation_id, message_id):
    async with async_session_factory() as session:
        message = await session.get(Message, message_id)
        if message is not None:
            await session.delete(message)
        conversation = await session.get(Conversation, conversation_id)
        if conversation is not None:
            await session.delete(conversation)
        await session.commit()


class AppDbModelShapeTests(unittest.TestCase):
    """Proves the ORM models match the brief's Outputs exactly -- no
    extra columns (e.g. no `user_id` on Conversation, which the brief
    explicitly says to omit until F8's `users` table lands)."""

    def test_conversation_model_has_exactly_the_briefs_columns(self):
        columns = {c.name for c in inspect(Conversation).columns}
        self.assertEqual(
            columns,
            {"id", "title", "created_at"},
            "Conversation must have exactly id, title, created_at per "
            f"the brief's Outputs, got: {columns!r}",
        )

    def test_message_model_has_exactly_the_briefs_columns(self):
        columns = {c.name for c in inspect(Message).columns}
        self.assertEqual(
            columns,
            {"id", "conversation_id", "role", "content_json", "created_at"},
            "Message must have exactly id, conversation_id, role, "
            f"content_json, created_at per the brief's Outputs, got: {columns!r}",
        )

    def test_engine_authenticates_as_postgres_user(self):
        self.assertEqual(
            engine.url.username,
            os.environ["POSTGRES_USER"],
            "the app-schema pool must authenticate as POSTGRES_USER "
            "(insightpilot_owner), per the brief's Constraints -- it "
            "must never be the OLIST_RO_USER read-only role",
        )


class AppDbRoundTripTests(unittest.IsolatedAsyncioTestCase):
    async def test_insert_then_read_back_in_a_fresh_session_matches_values(self):
        title = "insightpilot test conversation - round trip"
        role = "user"
        content = {"question": "how many orders were delivered late?"}

        conversation_id, message_id = await _create_conversation_and_message(
            title, role, content
        )
        try:
            async with async_session_factory() as fresh_session:
                conversation = await fresh_session.get(Conversation, conversation_id)
                message = await fresh_session.get(Message, message_id)

            self.assertIsNotNone(
                conversation,
                "expected the committed conversation to be visible in a "
                "brand-new session (a real commit, not same-session "
                "visibility)",
            )
            self.assertEqual(conversation.title, title)
            self.assertIsNotNone(conversation.created_at)

            self.assertIsNotNone(
                message,
                "expected the committed message to be visible in a "
                "brand-new session",
            )
            self.assertEqual(message.conversation_id, conversation_id)
            self.assertEqual(message.role, role)
            self.assertEqual(message.content_json, content)
            self.assertIsNotNone(message.created_at)
        finally:
            await _delete_conversation_and_message(conversation_id, message_id)

    async def test_content_json_round_trips_arbitrary_nested_json(self):
        nested_content = {
            "summary": "Orders trended up 12% quarter over quarter.",
            "chart_spec": {
                "type": "bar",
                "series": [1, 2, 3, 4],
                "options": {"stacked": True, "color": None},
            },
            "table_sample": [
                {"order_id": "abc123", "total": 129.9},
                {"order_id": "def456", "total": None},
            ],
            "follow_ups": ["what about last quarter?", "break down by region"],
        }

        conversation_id, message_id = await _create_conversation_and_message(
            "insightpilot test conversation - json round trip",
            "assistant",
            nested_content,
        )
        try:
            async with async_session_factory() as fresh_session:
                message = await fresh_session.get(Message, message_id)

            self.assertIsNotNone(message)
            self.assertEqual(
                message.content_json,
                nested_content,
                "expected the nested dict to round-trip through the "
                "content_json JSONB column unchanged",
            )
        finally:
            await _delete_conversation_and_message(conversation_id, message_id)

    async def test_message_with_nonexistent_conversation_id_violates_fk_constraint(
        self,
    ):
        async with async_session_factory() as session:
            orphan_message = Message(
                conversation_id=_NONEXISTENT_CONVERSATION_ID,
                role="user",
                content_json={"question": "irrelevant"},
            )
            session.add(orphan_message)
            with self.assertRaises(
                IntegrityError,
                msg=(
                    "expected the messages.conversation_id -> "
                    "conversations.id foreign key to be enforced, but "
                    "committing a message pointing at a nonexistent "
                    "conversation id succeeded"
                ),
            ):
                await session.commit()
            await session.rollback()

    async def test_cleanup_deletes_rows_leaving_no_trace_for_repeat_runs(self):
        conversation_id, message_id = await _create_conversation_and_message(
            "insightpilot test conversation - cleanup check",
            "user",
            {"question": "does cleanup actually delete rows?"},
        )

        await _delete_conversation_and_message(conversation_id, message_id)

        async with async_session_factory() as fresh_session:
            conversation = await fresh_session.get(Conversation, conversation_id)
            message = await fresh_session.get(Message, message_id)

        self.assertIsNone(
            conversation,
            "expected the conversation row to be gone after the cleanup "
            "delete, so repeat test runs don't accumulate garbage rows",
        )
        self.assertIsNone(
            message,
            "expected the message row to be gone after the cleanup delete",
        )


if __name__ == "__main__":
    unittest.main()
