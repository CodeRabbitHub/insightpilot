"""
Tests for the pin-dashboard-card-endpoint brief
(plans/briefs/2026-08-06-pin-dashboard-card-endpoint.md): a real
`POST /api/dashboards/{dashboard_id}/cards` route on `app/main.py` that
takes a full card payload (title, question_text, sql_text,
chart_spec_json, position) and either creates one `DashboardCard` row
under that dashboard and returns it, or 404s immediately -- with zero DB
writes -- if the dashboard id doesn't exist.

Per the brief's Constraints, this endpoint never executes `sql_text` or
runs it through sqlglot -- it stores exactly what the caller supplies,
so there is no LLM call and no `setUpClass`-shared-billed-request
pattern here (unlike test_api_ask_stream.py/test_api_conversations.py's
conversation-message tests); plain `unittest.TestCase`/
`unittest.IsolatedAsyncioTestCase` against the real `TestClient` and the
real dev Postgres (no mocking the DB) is enough, matching the brief's
own guidance.

This is written before `app/main.py` grows this route -- it will fail to
import/collect until that implementation lands, which is expected and
correct for tests written before implementation.

DashboardCardHappyPathTests looks up the seeded "Overview" dashboard
(there must be exactly one, per the dashboard-persistence brief's seed)
via `test_app_db._get_overview_dashboard_ids()`, POSTs a full card
payload -- including a nested `chart_spec_json` dict, to prove the JSONB
column round-trips it unchanged through the HTTP layer -- and asserts:
the response has exactly the 8 fields the brief's Outputs specify
(id, dashboard_id, title, question_text, sql_text, chart_spec_json,
position, created_at) with the values just posted; the row genuinely
exists with those same values when queried through a brand-new
`async_session_factory` session (not just echoed back by the response);
and, after this test cleans up its own row via
`test_app_db._delete_dashboard_card()`, the seeded Overview dashboard
row itself is untouched -- this suite must never delete it, only the
cards it creates underneath it.

UnknownDashboardIdTests uses a large fixed sentinel dashboard id
(999_999_999) rather than "max existing id + 1", per this repo's
established convention (test_api_conversations.py's
UNKNOWN_CONVERSATION_ID), to avoid a race against dashboards
concurrently created by another instance of this suite (e.g. the
stop_verify hook running against the same live dev DB). It asserts the
route 404s and that zero DashboardCard rows exist with that
dashboard_id afterward -- the brief's "404 immediately (zero DB
writes)" requirement.
"""
import asyncio
import unittest

try:
    from fastapi.testclient import TestClient

    from app.main import app
except Exception as exc:  # noqa: BLE001 -- captured so setUp can report it
    TestClient = None
    app = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

try:
    from sqlalchemy import select

    from app.db.models import Dashboard, DashboardCard
    from app.db.session import async_session_factory
    from test_app_db import _delete_dashboard_card, _get_overview_dashboard_ids
except Exception as exc:  # noqa: BLE001 -- captured so setUp can report it
    select = None
    Dashboard = None
    DashboardCard = None
    async_session_factory = None
    _delete_dashboard_card = None
    _get_overview_dashboard_ids = None
    if _IMPORT_ERROR is None:
        _IMPORT_ERROR = exc


UNKNOWN_DASHBOARD_ID = 999_999_999

EXPECTED_RESPONSE_FIELDS = {
    "id",
    "dashboard_id",
    "title",
    "question_text",
    "sql_text",
    "chart_spec_json",
    "position",
    "created_at",
}


async def _cards_for_dashboard(dashboard_id):
    """DashboardCard rows for exactly this dashboard_id -- scoped so a
    concurrently running instance of this suite (e.g. the stop_verify
    hook) never affects this assertion."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(DashboardCard).where(DashboardCard.dashboard_id == dashboard_id)
        )
        return list(result.scalars().all())


class DashboardCardHappyPathTests(unittest.TestCase):
    """POSTing a full card payload to the seeded Overview dashboard must
    create exactly one real DashboardCard row and echo it back with
    exactly the fields the brief promises."""

    def setUp(self):
        if _IMPORT_ERROR is not None:
            self.fail(f"could not import required modules: {_IMPORT_ERROR!r}")

        overview_ids = asyncio.run(_get_overview_dashboard_ids())
        self.assertEqual(
            len(overview_ids),
            1,
            "expected exactly one seeded 'Overview' dashboard row to pin "
            f"a test card under, found {len(overview_ids)}: {overview_ids!r}",
        )
        self.dashboard_id = overview_ids[0]

        self.payload = {
            "title": "Late deliveries by month",
            "question_text": "how many orders were delivered late, by month?",
            "sql_text": (
                "select date_trunc('month', order_delivered_customer_date) as "
                "month, count(*) from olist.orders where "
                "order_delivered_customer_date > order_estimated_delivery_date "
                "group by 1"
            ),
            "chart_spec_json": {
                "type": "bar",
                "encoding": {
                    "x": {"field": "month", "type": "temporal"},
                    "y": {"field": "count", "type": "quantitative"},
                },
                "options": {"stacked": False, "colors": ["#1f77b4", "#ff7f0e"]},
            },
            "position": 0,
        }

        client = TestClient(app)
        self.response = client.post(
            f"/api/dashboards/{self.dashboard_id}/cards", json=self.payload
        )
        self.card_id = None
        if self.response.status_code == 200:
            self.card_id = self.response.json().get("id")

    def tearDown(self):
        if self.card_id is not None:
            asyncio.run(_delete_dashboard_card(self.card_id))

    def test_returns_200(self):
        self.assertEqual(
            self.response.status_code,
            200,
            "expected 200 for POST /api/dashboards/{id}/cards, matching "
            "this repo's create_conversation convention (plain insert-"
            f"and-return, not 201), got {self.response.status_code}: "
            f"{self.response.text}",
        )

    def test_response_has_exactly_the_briefs_eight_fields(self):
        body = self.response.json()
        self.assertEqual(
            set(body.keys()),
            EXPECTED_RESPONSE_FIELDS,
            "expected the response to have exactly id, dashboard_id, "
            "title, question_text, sql_text, chart_spec_json, position, "
            f"created_at per the brief's Outputs, got: {body!r}",
        )

    def test_response_dashboard_id_matches_the_url(self):
        body = self.response.json()
        self.assertEqual(body["dashboard_id"], self.dashboard_id)

    def test_response_id_is_an_int(self):
        body = self.response.json()
        self.assertIsInstance(
            body["id"], int, f"expected an int card id, got: {body['id']!r}"
        )

    def test_response_echoes_the_posted_title_question_and_sql(self):
        body = self.response.json()
        self.assertEqual(body["title"], self.payload["title"])
        self.assertEqual(body["question_text"], self.payload["question_text"])
        self.assertEqual(body["sql_text"], self.payload["sql_text"])

    def test_response_chart_spec_json_matches_the_nested_dict_posted(self):
        body = self.response.json()
        self.assertEqual(
            body["chart_spec_json"],
            self.payload["chart_spec_json"],
            "expected the posted nested chart_spec_json dict to be "
            f"echoed back unchanged, got: {body['chart_spec_json']!r}",
        )

    def test_response_position_matches_the_posted_value(self):
        body = self.response.json()
        self.assertEqual(body["position"], self.payload["position"])

    def test_response_has_a_created_at_timestamp(self):
        body = self.response.json()
        self.assertIsInstance(body["created_at"], str)
        self.assertGreater(len(body["created_at"].strip()), 0)

    def test_row_really_exists_in_a_fresh_session_with_the_posted_values(self):
        self.assertIsNotNone(
            self.card_id,
            "no card_id was captured -- the POST must have failed, see "
            "the other failures above",
        )

        async def _fetch():
            async with async_session_factory() as fresh_session:
                return await fresh_session.get(DashboardCard, self.card_id)

        card = asyncio.run(_fetch())
        self.assertIsNotNone(
            card,
            "expected the card created by POST /api/dashboards/{id}/cards "
            "to be visible in a brand-new session (a real commit, not "
            "just an in-memory response echo)",
        )
        self.assertEqual(card.dashboard_id, self.dashboard_id)
        self.assertEqual(card.title, self.payload["title"])
        self.assertEqual(card.question_text, self.payload["question_text"])
        self.assertEqual(card.sql_text, self.payload["sql_text"])
        self.assertEqual(
            card.chart_spec_json,
            self.payload["chart_spec_json"],
            "expected the nested chart_spec_json dict to round-trip "
            "through the JSONB column unchanged",
        )
        self.assertEqual(card.position, self.payload["position"])
        self.assertIsNotNone(card.created_at)

    def test_overview_dashboard_survives_this_tests_cleanup(self):
        # tearDown deletes only the DashboardCard this test created; the
        # seeded Overview dashboard row itself must never be deleted by
        # this suite. Re-run the lookup after the response has been
        # captured (setUp already created the card) to prove the
        # dashboard row is still there right now, then let tearDown
        # clean up the card as usual.
        overview_ids = asyncio.run(_get_overview_dashboard_ids())
        self.assertIn(
            self.dashboard_id,
            overview_ids,
            "expected the seeded Overview dashboard row to still exist "
            "after pinning a card under it -- it must never be deleted "
            "by this suite, only the dashboard_cards it creates",
        )


class UnknownDashboardIdTests(unittest.TestCase):
    """POST /api/dashboards/{id}/cards against a dashboard id that does
    not exist must 404, with zero DashboardCard rows written under that
    id. Uses a large fixed sentinel id (999_999_999) rather than "max
    existing id + 1" to avoid a race against dashboards concurrently
    created by another instance of this suite."""

    def setUp(self):
        if _IMPORT_ERROR is not None:
            self.fail(f"could not import required modules: {_IMPORT_ERROR!r}")

    def _post_card_to_unknown_dashboard(self):
        client = TestClient(app)
        return client.post(
            f"/api/dashboards/{UNKNOWN_DASHBOARD_ID}/cards",
            json={
                "title": "should never be created",
                "question_text": "irrelevant for this test",
                "sql_text": "select 1",
                "chart_spec_json": {"type": "bar"},
                "position": 0,
            },
        )

    def test_returns_404(self):
        response = self._post_card_to_unknown_dashboard()
        self.assertEqual(
            response.status_code,
            404,
            "expected 404 for an unknown dashboard id, got "
            f"{response.status_code}: {response.text}",
        )

    def test_persists_no_dashboard_card_rows_for_that_dashboard_id(self):
        response = self._post_card_to_unknown_dashboard()
        self.assertEqual(response.status_code, 404)

        cards = asyncio.run(_cards_for_dashboard(UNKNOWN_DASHBOARD_ID))
        self.assertEqual(
            cards,
            [],
            "expected zero DashboardCard rows for the unknown sentinel "
            f"dashboard_id={UNKNOWN_DASHBOARD_ID} -- the brief requires "
            f"a 404 with zero DB writes, got: {[c.id for c in cards]!r}",
        )


if __name__ == "__main__":
    unittest.main()
