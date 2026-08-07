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

This file also covers the dashboard-fresh-on-view-get brief
(plans/briefs/2026-08-06-dashboard-fresh-on-view-get.md): a real
`GET /api/dashboards/{dashboard_id}` route that returns the dashboard's
own fields (`id`, `name`, `created_at`) plus every pinned card ordered
by `position` ascending, where each card carries its persisted fields
plus a `rows` field obtained by re-validating and re-executing that
card's stored `sql_text` fresh on every request -- never a cached or
stored value (there is no `rows` column on `DashboardCard` to cache in
the first place).

These GET tests seed their fixture cards directly via
`test_app_db._create_dashboard_card()` rather than through the POST
route above, per the brief's own guidance -- these tests care about
pre-existing rows on view, not the creation path.

`DashboardDetailHappyPathTests` pins two real cards under the seeded
Overview dashboard with their `position` values inserted out of numeric
order (position=1 first, position=0 second) to catch an implementation
that just returns insertion/id order instead of sorting by `position`;
proves "fresh, not stale" by independently re-running one seeded card's
exact `sql_text` through a fresh call to
`app.pipeline.execute_sql.execute_sql()` and asserting the GET
response's `rows` for that card match that independent execution
exactly, rather than trusting the endpoint's own claim. Assertions about
which cards/ids appear are scoped to the two ids this test itself
created (never a bare "the response has exactly N cards" count), so a
concurrently running instance of this suite (e.g. the stop_verify hook)
can never make this test flaky -- mirroring `_cards_for_dashboard`'s own
scoping rationale above.

`DashboardDetailNoOwnCardsTests` GETs the Overview dashboard while
creating no cards of its own, and asserts a 200 with a list-typed
`cards` field -- exercising the zero-or-more-cards loop for real without
asserting exact emptiness, since the shared dashboard may carry cards
from a concurrently running instance of this suite.

`DashboardDetailUnknownIdTests` 404s for the same
`UNKNOWN_DASHBOARD_ID` sentinel used by `UnknownDashboardIdTests` above.

`DashboardDetailBadCardSqlTests` pins one card whose `sql_text` is
deliberately invalid against the real catalog (a table that does not
exist), simulating schema drift since the card was pinned, and proves
the *whole* GET request 502s -- never a 200 with that card silently
dropped, never a partial/degraded card list -- per the brief's explicit
Constraint that per-card partial-failure rendering is out of scope this
slice.

Every test that creates a DashboardCard row cleans it up via
`test_app_db._delete_dashboard_card()` in tearDown, and none of these
tests ever deletes the seeded Overview `dashboards` row itself.

This file also covers the patch-dashboard-card-endpoint brief
(plans/briefs/2026-08-06-patch-dashboard-card-endpoint.md): a real
`PATCH /api/cards/{card_id}` route that partially updates an existing
`DashboardCard`'s `title` and/or `position` -- whichever the request
body supplies, leaving any omitted-or-null field unchanged -- and
returns it via the same `DashboardCardDetail` shape used by the POST
route above (no `rows`, since PATCH never touches or re-executes
`sql_text`). These tests seed their fixture card directly via
`test_app_db._create_dashboard_card()`, exactly like the GET tests
above, since this is a card-mutation test, not a creation-path test.

`PatchDashboardCardRenameOnlyTests` PATCHes only `title` and asserts the
response's `title` changed while `position` and every other persisted
field stayed at its seeded value -- confirmed both in the response body
and, separately, by re-fetching the row through a brand-new
`async_session_factory` session, matching this file's established
"verify via a fresh session, not just the echoed response" pattern.

`PatchDashboardCardRepositionOnlyTests` is the mirror image: PATCHes
only `position` and asserts `title` (and the other fields) are
untouched, again confirmed via both the response and a fresh session.

`PatchDashboardCardFalsyNewValuesTests` PATCHes `title: ""` and
`position: 0` -- both falsy but present -- against a card seeded with
non-falsy values, proving the route applies them (an `is not None`
check) rather than silently skipping them (a plain-truthiness check
would treat `""`/`0` the same as omitted).

`PatchDashboardCardIgnoresDisallowedFieldsTests` PATCHes a body that
also includes `dashboard_id`, `question_text`, `sql_text`, and
`chart_spec_json` alongside a legitimate `title` change, and asserts
all four disallowed fields stay exactly at their seeded values -- per
the brief's Constraint that only `title`/`position` are mutable via
this route.

`PatchDashboardCardBothFieldsTests` PATCHes `title` and `position`
together in one request and asserts both changed.

`PatchDashboardCardEmptyBodyNoopTests` PATCHes an empty `{}` body and
asserts a 200 (explicitly not a 422) with every field -- including
`title` and `position` -- unchanged from the seeded values, per the
brief's "supplying neither is a no-op 200" Constraint.

`PatchDashboardCardUnknownIdTests` PATCHes the same large fixed sentinel
id convention as `UnknownDashboardIdTests`/`DashboardDetailUnknownIdTests`
above (here named `UNKNOWN_CARD_ID`) and asserts a 404 with a `detail`
string in the body, matching this file's existing loose 404-detail
convention (a `detail` key present and string-typed, not an exact-text
assertion) used by `DashboardDetailUnknownIdTests` above.

This file also covers the delete-dashboard-card-endpoint brief
(plans/briefs/2026-08-07-delete-dashboard-card-endpoint.md): a real
`DELETE /api/cards/{card_id}` route that deletes exactly one
`DashboardCard` row by id and returns 204 with no body, or 404s with
the exact body `{"detail": "card not found"}` (matching
`patch_dashboard_card`'s message) if the id doesn't exist, with zero
writes in that case, and never touches the parent `Dashboard` row or
any sibling cards.

`DeleteDashboardCardHappyPathTests` seeds one card under the seeded
Overview dashboard via `test_app_db._create_dashboard_card()`, DELETEs
it via `TestClient`, and asserts: the response is 204 with an empty
body; and, separately, a fresh `_fetch_card()` call afterward returns
`None` -- the row is genuinely gone, not just claimed gone by the
response -- matching this file's established "verify via a fresh
session" pattern. Since the card is deleted by the test itself, tearDown
explicitly does not re-delete it (a no-op call would still be safe per
`_delete_dashboard_card`'s own `if card is not None` guard, but this
suite is explicit about the row already being gone).

`DeleteDashboardCardUnknownIdTests` DELETEs the same `UNKNOWN_CARD_ID`
sentinel used above and asserts an exact-match 404 body,
`{"detail": "card not found"}` -- unlike this file's looser
"has a detail string" 404 checks elsewhere, this brief's Constraints
call for that exact message -- plus a fresh `_fetch_card()` proving no
phantom row exists at that id.

`DeleteDashboardCardSiblingIsolationTests` seeds two cards under the
seeded Overview dashboard, DELETEs only the first, and asserts the first
is gone (fresh fetch returns `None`) while the second (sibling) card's
persisted fields are completely unchanged, and the Overview dashboard
row itself still exists -- proving the route touches exactly one row,
never the parent `Dashboard` or sibling `DashboardCard` rows. tearDown
cleans up the surviving second card.
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

try:
    from app.pipeline.execute_sql import execute_sql
    from test_app_db import _create_dashboard_card
except Exception as exc:  # noqa: BLE001 -- captured so setUp can report it
    execute_sql = None
    _create_dashboard_card = None
    if _IMPORT_ERROR is None:
        _IMPORT_ERROR = exc


UNKNOWN_DASHBOARD_ID = 999_999_999
UNKNOWN_CARD_ID = 999_999_999

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

EXPECTED_CARD_WITH_ROWS_FIELDS = EXPECTED_RESPONSE_FIELDS | {"rows"}

EXPECTED_DASHBOARD_DETAIL_FIELDS = {"id", "name", "created_at", "cards"}


async def _cards_for_dashboard(dashboard_id):
    """DashboardCard rows for exactly this dashboard_id -- scoped so a
    concurrently running instance of this suite (e.g. the stop_verify
    hook) never affects this assertion."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(DashboardCard).where(DashboardCard.dashboard_id == dashboard_id)
        )
        return list(result.scalars().all())


async def _fetch_card(card_id):
    async with async_session_factory() as session:
        return await session.get(DashboardCard, card_id)


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


class DashboardDetailHappyPathTests(unittest.TestCase):
    """GET /api/dashboards/{id} against the seeded Overview dashboard,
    with two real DashboardCard rows pinned directly via
    test_app_db._create_dashboard_card() with their `position` values
    inserted out of numeric order (position=1 first, position=0
    second), must return the dashboard's own fields plus both cards --
    ordered by position ascending, never insertion order -- each
    carrying fresh `rows` obtained by re-executing its persisted
    `sql_text` on this very request, not a stored/cached value (there is
    no `rows` column on DashboardCard to cache in the first place)."""

    def setUp(self):
        if _IMPORT_ERROR is not None:
            self.fail(f"could not import required modules: {_IMPORT_ERROR!r}")

        overview_ids = asyncio.run(_get_overview_dashboard_ids())
        self.assertEqual(
            len(overview_ids),
            1,
            "expected exactly one seeded 'Overview' dashboard row to pin "
            f"test cards under, found {len(overview_ids)}: {overview_ids!r}",
        )
        self.dashboard_id = overview_ids[0]

        # Inserted out of numeric order on purpose: the position=1 card
        # is created FIRST, the position=0 card SECOND. A correct
        # implementation must still return the position=0 card first.
        self.second_sql = "select 1 as n"
        self.second_card_id = asyncio.run(
            _create_dashboard_card(
                self.dashboard_id,
                "Second card (position 1)",
                "irrelevant question text for this test",
                self.second_sql,
                {"type": "bar"},
                1,
            )
        )
        self.first_sql = "select count(*) from olist.orders"
        self.first_card_id = asyncio.run(
            _create_dashboard_card(
                self.dashboard_id,
                "First card (position 0)",
                "how many orders are there in total?",
                self.first_sql,
                {"type": "number"},
                0,
            )
        )

        client = TestClient(app)
        self.response = client.get(f"/api/dashboards/{self.dashboard_id}")

    def tearDown(self):
        asyncio.run(_delete_dashboard_card(self.first_card_id))
        asyncio.run(_delete_dashboard_card(self.second_card_id))

    def test_returns_200(self):
        self.assertEqual(
            self.response.status_code,
            200,
            "expected 200 for GET /api/dashboards/{id}, got "
            f"{self.response.status_code}: {self.response.text}",
        )

    def test_response_has_exactly_the_dashboard_level_fields(self):
        body = self.response.json()
        self.assertEqual(
            set(body.keys()),
            EXPECTED_DASHBOARD_DETAIL_FIELDS,
            "expected exactly id, name, created_at, cards per the "
            f"brief's DashboardDetail model, got: {body!r}",
        )

    def test_response_id_and_name_match_the_seeded_overview_dashboard(self):
        body = self.response.json()
        self.assertEqual(body["id"], self.dashboard_id)
        self.assertEqual(body["name"], "Overview")

    def test_response_has_a_created_at_timestamp(self):
        body = self.response.json()
        self.assertIsInstance(body["created_at"], str)
        self.assertGreater(len(body["created_at"].strip()), 0)

    def test_response_includes_both_cards_this_test_pinned(self):
        # Scoped to just this test's own two card ids rather than an
        # exact-count assertion over the whole cards list, so a
        # concurrently running instance of this suite (e.g. the
        # stop_verify hook) can never make this assertion flaky.
        body = self.response.json()
        card_ids = {c["id"] for c in body["cards"]}
        self.assertTrue(
            {self.first_card_id, self.second_card_id} <= card_ids,
            "expected both cards this test pinned to appear in the "
            f"response, got card ids: {card_ids!r}",
        )

    def test_cards_are_ordered_by_position_ascending_not_insertion_order(self):
        body = self.response.json()
        ids_in_response_order = [
            c["id"]
            for c in body["cards"]
            if c["id"] in (self.first_card_id, self.second_card_id)
        ]
        self.assertEqual(
            ids_in_response_order,
            [self.first_card_id, self.second_card_id],
            "expected the position=0 card (inserted SECOND) before the "
            "position=1 card (inserted FIRST) -- ordering must follow "
            f"`position`, not insertion/id order, got card ids in this "
            f"response order: {ids_in_response_order!r}",
        )

    def test_every_card_in_the_response_has_exactly_the_persisted_fields_plus_rows(
        self,
    ):
        body = self.response.json()
        self.assertGreater(
            len(body["cards"]), 0, "expected at least the two pinned test cards"
        )
        for card in body["cards"]:
            self.assertEqual(
                set(card.keys()),
                EXPECTED_CARD_WITH_ROWS_FIELDS,
                "expected each card to carry exactly the persisted "
                "DashboardCard fields (id, dashboard_id, title, "
                "question_text, sql_text, chart_spec_json, position, "
                f"created_at) plus a fresh 'rows' field, got: {card!r}",
            )

    def test_each_card_echoes_its_persisted_fields_unchanged(self):
        body = self.response.json()
        cards_by_id = {c["id"]: c for c in body["cards"]}

        first = cards_by_id[self.first_card_id]
        self.assertEqual(first["dashboard_id"], self.dashboard_id)
        self.assertEqual(first["title"], "First card (position 0)")
        self.assertEqual(
            first["question_text"], "how many orders are there in total?"
        )
        self.assertEqual(first["sql_text"], self.first_sql)
        self.assertEqual(first["chart_spec_json"], {"type": "number"})
        self.assertEqual(first["position"], 0)

        second = cards_by_id[self.second_card_id]
        self.assertEqual(second["dashboard_id"], self.dashboard_id)
        self.assertEqual(second["title"], "Second card (position 1)")
        self.assertEqual(
            second["question_text"], "irrelevant question text for this test"
        )
        self.assertEqual(second["sql_text"], self.second_sql)
        self.assertEqual(second["chart_spec_json"], {"type": "bar"})
        self.assertEqual(second["position"], 1)

    def test_rows_match_an_independent_real_execute_sql_call_on_the_same_sql_text(
        self,
    ):
        # This is the "fresh on view" proof: there is no rows column on
        # DashboardCard to have served a cached value from, so the only
        # way the endpoint could produce this rows value is by actually
        # re-running sql_text on this request. Confirmed here by
        # independently re-running the exact same sql_text through the
        # same real execution path and asserting equality.
        body = self.response.json()
        cards_by_id = {c["id"]: c for c in body["cards"]}

        independent_rows = asyncio.run(execute_sql(self.first_sql))
        self.assertEqual(
            cards_by_id[self.first_card_id]["rows"],
            independent_rows,
            "expected the response's rows for this card to match an "
            "independent, real app.pipeline.execute_sql.execute_sql() "
            "call on the exact same sql_text, proving the endpoint "
            "re-executed it fresh rather than returning a stale/cached "
            "value",
        )

    def test_rows_field_is_a_nonempty_list_of_dicts(self):
        body = self.response.json()
        cards_by_id = {c["id"]: c for c in body["cards"]}
        rows = cards_by_id[self.first_card_id]["rows"]
        self.assertIsInstance(rows, list)
        self.assertGreater(len(rows), 0, f"expected non-empty rows, got: {rows!r}")
        for row in rows:
            self.assertIsInstance(row, dict)

    def test_overview_dashboard_survives_this_tests_cleanup(self):
        overview_ids = asyncio.run(_get_overview_dashboard_ids())
        self.assertIn(
            self.dashboard_id,
            overview_ids,
            "expected the seeded Overview dashboard row to still exist "
            "after this test's GET -- it must never be deleted by this "
            "suite, only the dashboard_cards it creates",
        )


class DashboardDetailNoOwnCardsTests(unittest.TestCase):
    """GET /api/dashboards/{id} must not assume the card list is
    non-empty -- this creates no cards of its own and asserts the
    response is still a well-formed 200 with a list-typed `cards` field
    (the zero-cards code path: the per-card validate/execute loop must
    run zero times cleanly, not error on an empty result set).

    Cannot assert `cards == []` -- the Overview dashboard is shared with
    every other test/process against this live dev Postgres (PRD F6:
    "one default dashboard"), and this brief's Out-of-scope forbids
    creating another one to isolate against), so a concurrently running
    instance of this suite may have its own cards pinned at the same
    moment. Asserting the *type* of `cards` still exercises the
    zero-or-more-cards loop for real, without an exact-count assertion
    that would be flaky under concurrency."""

    def setUp(self):
        if _IMPORT_ERROR is not None:
            self.fail(f"could not import required modules: {_IMPORT_ERROR!r}")

        overview_ids = asyncio.run(_get_overview_dashboard_ids())
        self.assertEqual(
            len(overview_ids),
            1,
            "expected exactly one seeded 'Overview' dashboard row, found "
            f"{len(overview_ids)}: {overview_ids!r}",
        )
        self.dashboard_id = overview_ids[0]

        client = TestClient(app)
        self.response = client.get(f"/api/dashboards/{self.dashboard_id}")

    def test_returns_200(self):
        self.assertEqual(
            self.response.status_code,
            200,
            "expected 200 for GET /api/dashboards/{id} with no cards of "
            f"this test's own, got {self.response.status_code}: "
            f"{self.response.text}",
        )

    def test_cards_field_is_a_list(self):
        body = self.response.json()
        self.assertIsInstance(
            body["cards"],
            list,
            f"expected 'cards' to be a list even with none pinned by "
            f"this test, got: {body['cards']!r}",
        )


class DashboardDetailUnknownIdTests(unittest.TestCase):
    """GET /api/dashboards/{id} against a dashboard id that does not
    exist must 404. Uses the same large fixed sentinel id
    (999_999_999) as UnknownDashboardIdTests above, for the same
    race-avoidance reason."""

    def setUp(self):
        if _IMPORT_ERROR is not None:
            self.fail(f"could not import required modules: {_IMPORT_ERROR!r}")

        client = TestClient(app)
        self.response = client.get(f"/api/dashboards/{UNKNOWN_DASHBOARD_ID}")

    def test_returns_404(self):
        self.assertEqual(
            self.response.status_code,
            404,
            "expected 404 for GET /api/dashboards/{id} with an unknown "
            f"dashboard id, got {self.response.status_code}: "
            f"{self.response.text}",
        )

    def test_404_response_body_has_a_detail_string(self):
        body = self.response.json()
        self.assertIn(
            "detail",
            body,
            f"expected a 'detail' key in the 404 error body, got: {body!r}",
        )
        self.assertIsInstance(body["detail"], str)


class DashboardDetailBadCardSqlTests(unittest.TestCase):
    """One pinned card whose sql_text no longer validates/executes (here,
    a reference to a table that does not exist in the real catalog,
    simulating schema drift since the card was pinned) must fail the
    WHOLE GET request with 502 -- never a 200 with that card silently
    dropped, never a partial/degraded card list. Matches /api/ask's
    existing upstream-pipeline-failure convention
    (HTTPException(status_code=502, detail=str(exc))).

    Known, accepted tradeoff: the brief's Out-of-scope forbids creating a
    second dashboard (PRD F6: "one default dashboard"), so this test's
    broken card is necessarily pinned onto the one real seeded Overview
    dashboard for the brief lifetime of this test. Any other GET against
    that same dashboard_id concurrently in flight (e.g. another instance
    of this suite, or the stop_verify hook) would also observe a 502
    during that narrow window -- correct per-request behavior, but a
    real, if brief and low-probability, side effect on shared state.
    Accepted here rather than avoided, since there is no in-scope way to
    isolate this fixture from the one shared dashboard."""

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

        self.bad_card_id = asyncio.run(
            _create_dashboard_card(
                self.dashboard_id,
                "Card with SQL that no longer validates",
                "irrelevant question text for this test",
                "select * from nonexistent_table",
                {"type": "bar"},
                0,
            )
        )

        client = TestClient(app)
        self.response = client.get(f"/api/dashboards/{self.dashboard_id}")

    def tearDown(self):
        asyncio.run(_delete_dashboard_card(self.bad_card_id))

    def test_returns_502_not_200(self):
        self.assertEqual(
            self.response.status_code,
            502,
            "expected 502 when a pinned card's sql_text no longer "
            f"validates or executes, got {self.response.status_code}: "
            f"{self.response.text}",
        )

    def test_502_response_body_has_a_detail_string(self):
        body = self.response.json()
        self.assertIn(
            "detail",
            body,
            f"expected a 'detail' key in the 502 error body, got: {body!r}",
        )
        self.assertIsInstance(body["detail"], str)

    def test_502_response_body_has_no_cards_field(self):
        # Per the brief's Constraint: a bad card must fail the WHOLE
        # request -- no partial card list with that one card silently
        # dropped, no degraded 200.
        body = self.response.json()
        self.assertNotIn(
            "cards",
            body,
            "expected the 502 error body to carry no 'cards' field at "
            f"all -- no partial/degraded card list, got: {body!r}",
        )

    def test_overview_dashboard_survives_this_tests_cleanup(self):
        overview_ids = asyncio.run(_get_overview_dashboard_ids())
        self.assertIn(
            self.dashboard_id,
            overview_ids,
            "expected the seeded Overview dashboard row to still exist "
            "after this test -- it must never be deleted by this suite, "
            "only the dashboard_cards it creates",
        )


class PatchDashboardCardRenameOnlyTests(unittest.TestCase):
    """PATCH /api/cards/{id} with only `title` in the body must update
    just that column -- `position` and every other persisted field must
    stay exactly at its seeded value. Confirmed both via the response
    body and via a fresh async_session_factory session query, matching
    this file's established "verify via a fresh session, not just the
    echoed response" pattern (see DashboardCardHappyPathTests above)."""

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

        self.seeded_title = "Original title before PATCH"
        self.seeded_question_text = "how many orders are there in total?"
        self.seeded_sql_text = "select count(*) from olist.orders"
        self.seeded_chart_spec_json = {"type": "number"}
        self.seeded_position = 3

        self.card_id = asyncio.run(
            _create_dashboard_card(
                self.dashboard_id,
                self.seeded_title,
                self.seeded_question_text,
                self.seeded_sql_text,
                self.seeded_chart_spec_json,
                self.seeded_position,
            )
        )

        client = TestClient(app)
        self.new_title = "Renamed title after PATCH"
        self.response = client.patch(
            f"/api/cards/{self.card_id}", json={"title": self.new_title}
        )

    def tearDown(self):
        asyncio.run(_delete_dashboard_card(self.card_id))

    def test_returns_200(self):
        self.assertEqual(
            self.response.status_code,
            200,
            "expected 200 for a rename-only PATCH /api/cards/{id}, got "
            f"{self.response.status_code}: {self.response.text}",
        )

    def test_response_has_exactly_the_briefs_eight_fields(self):
        body = self.response.json()
        self.assertEqual(
            set(body.keys()),
            EXPECTED_RESPONSE_FIELDS,
            "expected the PATCH response to reuse DashboardCardDetail's "
            "exact 8 fields (no 'rows', since PATCH never touches "
            f"sql_text), got: {body!r}",
        )

    def test_response_title_is_updated(self):
        body = self.response.json()
        self.assertEqual(
            body["title"],
            self.new_title,
            f"expected the response title to be the new value, got: {body!r}",
        )

    def test_response_position_and_other_fields_are_unchanged(self):
        body = self.response.json()
        self.assertEqual(
            body["position"],
            self.seeded_position,
            "expected position to be untouched by a title-only PATCH, "
            f"got: {body!r}",
        )
        self.assertEqual(body["dashboard_id"], self.dashboard_id)
        self.assertEqual(body["question_text"], self.seeded_question_text)
        self.assertEqual(body["sql_text"], self.seeded_sql_text)
        self.assertEqual(body["chart_spec_json"], self.seeded_chart_spec_json)

    def test_row_really_updated_in_a_fresh_session(self):
        card = asyncio.run(_fetch_card(self.card_id))
        self.assertIsNotNone(
            card,
            "expected the patched card to still exist in a brand-new "
            "session",
        )
        self.assertEqual(
            card.title,
            self.new_title,
            "expected the persisted row's title column to reflect the "
            "PATCH, not just the echoed response",
        )
        self.assertEqual(card.position, self.seeded_position)
        self.assertEqual(card.dashboard_id, self.dashboard_id)
        self.assertEqual(card.question_text, self.seeded_question_text)
        self.assertEqual(card.sql_text, self.seeded_sql_text)
        self.assertEqual(card.chart_spec_json, self.seeded_chart_spec_json)


class PatchDashboardCardRepositionOnlyTests(unittest.TestCase):
    """PATCH /api/cards/{id} with only `position` in the body must
    update just that column -- `title` and every other persisted field
    must stay exactly at its seeded value. Confirmed both via the
    response body and via a fresh session, mirroring
    PatchDashboardCardRenameOnlyTests above."""

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

        self.seeded_title = "Title that must survive a reposition-only PATCH"
        self.seeded_question_text = "irrelevant question text for this test"
        self.seeded_sql_text = "select 1 as n"
        self.seeded_chart_spec_json = {"type": "bar"}
        self.seeded_position = 0

        self.card_id = asyncio.run(
            _create_dashboard_card(
                self.dashboard_id,
                self.seeded_title,
                self.seeded_question_text,
                self.seeded_sql_text,
                self.seeded_chart_spec_json,
                self.seeded_position,
            )
        )

        client = TestClient(app)
        self.new_position = 7
        self.response = client.patch(
            f"/api/cards/{self.card_id}", json={"position": self.new_position}
        )

    def tearDown(self):
        asyncio.run(_delete_dashboard_card(self.card_id))

    def test_returns_200(self):
        self.assertEqual(
            self.response.status_code,
            200,
            "expected 200 for a reposition-only PATCH /api/cards/{id}, "
            f"got {self.response.status_code}: {self.response.text}",
        )

    def test_response_position_is_updated(self):
        body = self.response.json()
        self.assertEqual(
            body["position"],
            self.new_position,
            f"expected the response position to be the new value, got: {body!r}",
        )

    def test_response_title_and_other_fields_are_unchanged(self):
        body = self.response.json()
        self.assertEqual(
            body["title"],
            self.seeded_title,
            "expected title to be untouched by a position-only PATCH, "
            f"got: {body!r}",
        )
        self.assertEqual(body["dashboard_id"], self.dashboard_id)
        self.assertEqual(body["question_text"], self.seeded_question_text)
        self.assertEqual(body["sql_text"], self.seeded_sql_text)
        self.assertEqual(body["chart_spec_json"], self.seeded_chart_spec_json)

    def test_row_really_updated_in_a_fresh_session(self):
        card = asyncio.run(_fetch_card(self.card_id))
        self.assertIsNotNone(card)
        self.assertEqual(
            card.position,
            self.new_position,
            "expected the persisted row's position column to reflect "
            "the PATCH, not just the echoed response",
        )
        self.assertEqual(card.title, self.seeded_title)
        self.assertEqual(card.dashboard_id, self.dashboard_id)
        self.assertEqual(card.question_text, self.seeded_question_text)
        self.assertEqual(card.sql_text, self.seeded_sql_text)
        self.assertEqual(card.chart_spec_json, self.seeded_chart_spec_json)


class PatchDashboardCardFalsyNewValuesTests(unittest.TestCase):
    """PATCH /api/cards/{id} with new values that are falsy but present
    -- `position: 0` and `title: ""` -- must still apply them, proving
    the route checks `is not None` rather than plain truthiness. Seeds
    a card whose title/position are both non-falsy so a truthiness-based
    implementation (which would silently skip these) is distinguishable
    from a None-check-based one (which applies them)."""

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

        self.seeded_title = "Non-empty title before a falsy-value PATCH"
        self.seeded_position = 4
        self.card_id = asyncio.run(
            _create_dashboard_card(
                self.dashboard_id,
                self.seeded_title,
                "irrelevant question text for this test",
                "select 1 as n",
                {"type": "bar"},
                self.seeded_position,
            )
        )

        client = TestClient(app)
        self.response = client.patch(
            f"/api/cards/{self.card_id}", json={"title": "", "position": 0}
        )

    def tearDown(self):
        asyncio.run(_delete_dashboard_card(self.card_id))

    def test_returns_200(self):
        self.assertEqual(
            self.response.status_code,
            200,
            "expected 200 for a falsy-new-values PATCH /api/cards/{id}, "
            f"got {self.response.status_code}: {self.response.text}",
        )

    def test_response_title_and_position_are_applied_not_skipped(self):
        body = self.response.json()
        self.assertEqual(
            body["title"],
            "",
            "expected an empty-string title to be applied, not skipped "
            f"as falsy, got: {body!r}",
        )
        self.assertEqual(
            body["position"],
            0,
            "expected a zero position to be applied, not skipped as "
            f"falsy, got: {body!r}",
        )

    def test_row_really_updated_in_a_fresh_session(self):
        card = asyncio.run(_fetch_card(self.card_id))
        self.assertIsNotNone(card)
        self.assertEqual(
            card.title,
            "",
            "expected the persisted row's title to be the applied empty "
            "string, not the seeded non-empty value",
        )
        self.assertEqual(
            card.position,
            0,
            "expected the persisted row's position to be the applied "
            "zero, not the seeded non-zero value",
        )


class PatchDashboardCardIgnoresDisallowedFieldsTests(unittest.TestCase):
    """PATCH /api/cards/{id} with `sql_text`, `dashboard_id`,
    `chart_spec_json`, and `question_text` all present in the body
    (alongside a legitimate `title` change) must leave every one of
    those four columns exactly at its seeded value -- per the brief's
    Constraint that only `title`/`position` are mutable via this route
    and renaming/repositioning never touches or re-validates `sql_text`.
    `PatchDashboardCardRequest` simply has no fields for them, so
    Pydantic silently drops these extra keys, but this test proves that
    behavior at the HTTP layer rather than leaving it as a structural
    assumption -- confirmed both via the response and a fresh session."""

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

        self.seeded_question_text = "how many orders are there in total?"
        self.seeded_sql_text = "select count(*) from olist.orders"
        self.seeded_chart_spec_json = {"type": "number"}
        self.seeded_position = 1
        self.card_id = asyncio.run(
            _create_dashboard_card(
                self.dashboard_id,
                "Original title before a disallowed-fields PATCH",
                self.seeded_question_text,
                self.seeded_sql_text,
                self.seeded_chart_spec_json,
                self.seeded_position,
            )
        )

        client = TestClient(app)
        self.new_title = "Renamed, disallowed fields ignored"
        self.response = client.patch(
            f"/api/cards/{self.card_id}",
            json={
                "title": self.new_title,
                "dashboard_id": self.dashboard_id + 1,
                "question_text": "an entirely different question",
                "sql_text": "select * from olist.nonexistent_table",
                "chart_spec_json": {"type": "pie"},
            },
        )

    def tearDown(self):
        asyncio.run(_delete_dashboard_card(self.card_id))

    def test_returns_200(self):
        self.assertEqual(
            self.response.status_code,
            200,
            "expected 200 for a PATCH whose body includes disallowed "
            f"extra fields alongside a legitimate title, got "
            f"{self.response.status_code}: {self.response.text}",
        )

    def test_response_title_updated_but_disallowed_fields_unchanged(self):
        body = self.response.json()
        self.assertEqual(body["title"], self.new_title)
        self.assertEqual(
            body["dashboard_id"],
            self.dashboard_id,
            "dashboard_id must never change via this route, got: "
            f"{body!r}",
        )
        self.assertEqual(body["question_text"], self.seeded_question_text)
        self.assertEqual(body["sql_text"], self.seeded_sql_text)
        self.assertEqual(body["chart_spec_json"], self.seeded_chart_spec_json)

    def test_row_disallowed_fields_unchanged_in_a_fresh_session(self):
        card = asyncio.run(_fetch_card(self.card_id))
        self.assertIsNotNone(card)
        self.assertEqual(card.title, self.new_title)
        self.assertEqual(card.dashboard_id, self.dashboard_id)
        self.assertEqual(card.question_text, self.seeded_question_text)
        self.assertEqual(card.sql_text, self.seeded_sql_text)
        self.assertEqual(card.chart_spec_json, self.seeded_chart_spec_json)


class PatchDashboardCardBothFieldsTests(unittest.TestCase):
    """PATCH /api/cards/{id} with both `title` and `position` supplied
    together in one request must update both columns."""

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

        self.seeded_title = "Original title before a combined PATCH"
        self.seeded_position = 2
        self.card_id = asyncio.run(
            _create_dashboard_card(
                self.dashboard_id,
                self.seeded_title,
                "irrelevant question text for this test",
                "select 1 as n",
                {"type": "bar"},
                self.seeded_position,
            )
        )

        client = TestClient(app)
        self.new_title = "Renamed by a combined PATCH"
        self.new_position = 9
        self.response = client.patch(
            f"/api/cards/{self.card_id}",
            json={"title": self.new_title, "position": self.new_position},
        )

    def tearDown(self):
        asyncio.run(_delete_dashboard_card(self.card_id))

    def test_returns_200(self):
        self.assertEqual(
            self.response.status_code,
            200,
            "expected 200 for a combined title+position PATCH "
            f"/api/cards/{{id}}, got {self.response.status_code}: "
            f"{self.response.text}",
        )

    def test_response_title_and_position_both_updated(self):
        body = self.response.json()
        self.assertEqual(body["title"], self.new_title)
        self.assertEqual(body["position"], self.new_position)

    def test_row_really_updated_in_a_fresh_session(self):
        card = asyncio.run(_fetch_card(self.card_id))
        self.assertIsNotNone(card)
        self.assertEqual(card.title, self.new_title)
        self.assertEqual(card.position, self.new_position)


class PatchDashboardCardEmptyBodyNoopTests(unittest.TestCase):
    """PATCH /api/cards/{id} with an empty `{}` body must be a 200 no-op
    -- explicitly not a 422 -- with every field, including `title` and
    `position`, unchanged from the seeded values."""

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

        self.seeded_title = "Title that must survive an empty-body PATCH"
        self.seeded_question_text = "irrelevant question text for this test"
        self.seeded_sql_text = "select 1 as n"
        self.seeded_chart_spec_json = {"type": "bar"}
        self.seeded_position = 5

        self.card_id = asyncio.run(
            _create_dashboard_card(
                self.dashboard_id,
                self.seeded_title,
                self.seeded_question_text,
                self.seeded_sql_text,
                self.seeded_chart_spec_json,
                self.seeded_position,
            )
        )

        client = TestClient(app)
        self.response = client.patch(f"/api/cards/{self.card_id}", json={})

    def tearDown(self):
        asyncio.run(_delete_dashboard_card(self.card_id))

    def test_returns_200_not_422(self):
        self.assertNotEqual(
            self.response.status_code,
            422,
            "an empty PATCH body must not be treated as a validation "
            f"error per the brief's Constraints, got: {self.response.text}",
        )
        self.assertEqual(
            self.response.status_code,
            200,
            "expected 200 for an empty-body no-op PATCH /api/cards/{id}, "
            f"got {self.response.status_code}: {self.response.text}",
        )

    def test_response_every_field_unchanged_from_seeded_values(self):
        body = self.response.json()
        self.assertEqual(body["id"], self.card_id)
        self.assertEqual(body["dashboard_id"], self.dashboard_id)
        self.assertEqual(body["title"], self.seeded_title)
        self.assertEqual(body["question_text"], self.seeded_question_text)
        self.assertEqual(body["sql_text"], self.seeded_sql_text)
        self.assertEqual(body["chart_spec_json"], self.seeded_chart_spec_json)
        self.assertEqual(body["position"], self.seeded_position)

    def test_row_unchanged_in_a_fresh_session(self):
        card = asyncio.run(_fetch_card(self.card_id))
        self.assertIsNotNone(card)
        self.assertEqual(card.title, self.seeded_title)
        self.assertEqual(card.position, self.seeded_position)
        self.assertEqual(card.dashboard_id, self.dashboard_id)
        self.assertEqual(card.question_text, self.seeded_question_text)
        self.assertEqual(card.sql_text, self.seeded_sql_text)
        self.assertEqual(card.chart_spec_json, self.seeded_chart_spec_json)


class PatchDashboardCardUnknownIdTests(unittest.TestCase):
    """PATCH /api/cards/{id} against a card id that does not exist must
    404. Uses the same large fixed sentinel convention as
    UnknownDashboardIdTests/DashboardDetailUnknownIdTests above (here
    UNKNOWN_CARD_ID = 999_999_999), to avoid a race against cards
    concurrently created by another instance of this suite (e.g. the
    stop_verify hook running against the same live dev DB)."""

    def setUp(self):
        if _IMPORT_ERROR is not None:
            self.fail(f"could not import required modules: {_IMPORT_ERROR!r}")

        client = TestClient(app)
        self.response = client.patch(
            f"/api/cards/{UNKNOWN_CARD_ID}", json={"title": "should never apply"}
        )

    def test_returns_404(self):
        self.assertEqual(
            self.response.status_code,
            404,
            "expected 404 for PATCH /api/cards/{id} with an unknown "
            f"card id, got {self.response.status_code}: {self.response.text}",
        )

    def test_404_response_body_has_a_detail_string(self):
        # Matches this file's existing loose 404-detail convention (see
        # DashboardDetailUnknownIdTests above): a 'detail' key present
        # and string-typed, not an exact-text assertion.
        body = self.response.json()
        self.assertIn(
            "detail",
            body,
            f"expected a 'detail' key in the 404 error body, got: {body!r}",
        )
        self.assertIsInstance(body["detail"], str)


class DeleteDashboardCardHappyPathTests(unittest.TestCase):
    """DELETE /api/cards/{id} against a real, freshly-seeded card under
    the seeded Overview dashboard must return 204 with no response body,
    and the row must be genuinely gone -- confirmed by a fresh
    `_fetch_card()` call through a brand-new `async_session_factory`
    session, not just by trusting the response's status code, matching
    this file's established "verify via a fresh session" pattern (see
    DashboardCardHappyPathTests above)."""

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

        self.card_id = asyncio.run(
            _create_dashboard_card(
                self.dashboard_id,
                "Card that this test deletes",
                "irrelevant question text for this test",
                "select 1 as n",
                {"type": "bar"},
                0,
            )
        )

        client = TestClient(app)
        self.response = client.delete(f"/api/cards/{self.card_id}")

    def test_returns_204(self):
        self.assertEqual(
            self.response.status_code,
            204,
            "expected 204 No Content for DELETE /api/cards/{id} on an "
            f"existing card, got {self.response.status_code}: "
            f"{self.response.text}",
        )

    def test_response_body_is_empty(self):
        self.assertEqual(
            self.response.content,
            b"",
            "a 204 response must carry no body, got: "
            f"{self.response.content!r}",
        )

    def test_row_is_genuinely_gone_in_a_fresh_session(self):
        card = asyncio.run(_fetch_card(self.card_id))
        self.assertIsNone(
            card,
            "expected the deleted card to be genuinely gone when "
            "queried through a brand-new session, not just claimed "
            f"gone by the 204 response, got: {card!r}",
        )


class DeleteDashboardCardUnknownIdTests(unittest.TestCase):
    """DELETE /api/cards/{id} against a card id that does not exist must
    404 with the exact body `{"detail": "card not found"}`, per this
    brief's Constraints (matching `patch_dashboard_card`'s message) --
    unlike this file's looser "has a detail string" 404 checks used by
    PatchDashboardCardUnknownIdTests/DashboardDetailUnknownIdTests
    above, this brief calls for an exact match. Uses the same large
    fixed sentinel id (UNKNOWN_CARD_ID = 999_999_999) already defined in
    this file, for the same race-avoidance reason as those tests."""

    def setUp(self):
        if _IMPORT_ERROR is not None:
            self.fail(f"could not import required modules: {_IMPORT_ERROR!r}")

        client = TestClient(app)
        self.response = client.delete(f"/api/cards/{UNKNOWN_CARD_ID}")

    def test_returns_404(self):
        self.assertEqual(
            self.response.status_code,
            404,
            "expected 404 for DELETE /api/cards/{id} with an unknown "
            f"card id, got {self.response.status_code}: {self.response.text}",
        )

    def test_404_response_body_matches_the_exact_message(self):
        self.assertEqual(
            self.response.json(),
            {"detail": "card not found"},
            "expected the exact body {'detail': 'card not found'} per "
            "the brief's Constraints, got: "
            f"{self.response.json()!r}",
        )

    def test_no_phantom_row_exists_at_the_unknown_id(self):
        card = asyncio.run(_fetch_card(UNKNOWN_CARD_ID))
        self.assertIsNone(
            card,
            "expected no DashboardCard row to exist at the unknown "
            "sentinel id after a 404 DELETE -- zero writes, no phantom "
            f"row, got: {card!r}",
        )


class DeleteDashboardCardSiblingIsolationTests(unittest.TestCase):
    """Deleting one DashboardCard row via DELETE /api/cards/{id} must
    touch exactly that row -- never a sibling card under the same
    dashboard, and never the parent Dashboard row itself. Seeds two real
    cards under the seeded Overview dashboard, deletes only the first,
    and asserts the second card's persisted fields are completely
    unchanged and the Overview dashboard row still exists."""

    def setUp(self):
        if _IMPORT_ERROR is not None:
            self.fail(f"could not import required modules: {_IMPORT_ERROR!r}")

        overview_ids = asyncio.run(_get_overview_dashboard_ids())
        self.assertEqual(
            len(overview_ids),
            1,
            "expected exactly one seeded 'Overview' dashboard row to pin "
            f"test cards under, found {len(overview_ids)}: {overview_ids!r}",
        )
        self.dashboard_id = overview_ids[0]

        self.first_title = "First card -- this one gets deleted"
        self.first_question_text = "irrelevant question text for this test"
        self.first_sql_text = "select 1 as n"
        self.first_chart_spec_json = {"type": "bar"}
        self.first_position = 0
        self.first_card_id = asyncio.run(
            _create_dashboard_card(
                self.dashboard_id,
                self.first_title,
                self.first_question_text,
                self.first_sql_text,
                self.first_chart_spec_json,
                self.first_position,
            )
        )

        self.second_title = "Second card -- sibling, must survive"
        self.second_question_text = "how many orders are there in total?"
        self.second_sql_text = "select count(*) from olist.orders"
        self.second_chart_spec_json = {"type": "number"}
        self.second_position = 1
        self.second_card_id = asyncio.run(
            _create_dashboard_card(
                self.dashboard_id,
                self.second_title,
                self.second_question_text,
                self.second_sql_text,
                self.second_chart_spec_json,
                self.second_position,
            )
        )

        client = TestClient(app)
        self.response = client.delete(f"/api/cards/{self.first_card_id}")

    def tearDown(self):
        asyncio.run(_delete_dashboard_card(self.second_card_id))

    def test_returns_204(self):
        self.assertEqual(
            self.response.status_code,
            204,
            "expected 204 for deleting the first card, got "
            f"{self.response.status_code}: {self.response.text}",
        )

    def test_deleted_card_is_genuinely_gone(self):
        card = asyncio.run(_fetch_card(self.first_card_id))
        self.assertIsNone(
            card,
            f"expected the deleted first card to be gone, got: {card!r}",
        )

    def test_sibling_card_is_completely_unchanged(self):
        sibling = asyncio.run(_fetch_card(self.second_card_id))
        self.assertIsNotNone(
            sibling,
            "expected the sibling card to still exist after deleting "
            "the first card -- DELETE must touch exactly one row",
        )
        self.assertEqual(sibling.dashboard_id, self.dashboard_id)
        self.assertEqual(sibling.title, self.second_title)
        self.assertEqual(sibling.question_text, self.second_question_text)
        self.assertEqual(sibling.sql_text, self.second_sql_text)
        self.assertEqual(sibling.chart_spec_json, self.second_chart_spec_json)
        self.assertEqual(sibling.position, self.second_position)

    def test_overview_dashboard_row_still_exists(self):
        overview_ids = asyncio.run(_get_overview_dashboard_ids())
        self.assertIn(
            self.dashboard_id,
            overview_ids,
            "expected the seeded Overview dashboard row to still exist "
            "after deleting one of its cards -- the parent Dashboard "
            f"row must never be touched by this route, found: {overview_ids!r}",
        )


if __name__ == "__main__":
    unittest.main()
