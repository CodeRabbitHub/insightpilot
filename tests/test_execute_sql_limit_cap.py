"""
Pure, no-DB unit tests for the execute-sql brief's LIMIT-injection logic
(plans/briefs/2026-08-02-execute-sql.md): before any generated SQL is
allowed anywhere near the read-only asyncpg connection, a row cap must be
enforced by modifying the sqlglot-parsed statement -- never by
string-munging the raw SQL text -- per the brief's Constraints:

    - no existing LIMIT             -> a LIMIT of exactly `cap` is added
    - a looser existing LIMIT        -> tightened down to `cap`
    - a tighter existing LIMIT       -> left untouched, never loosened
      (the fixed question's real `LIMIT 5` must survive as-is)

These call directly into `cap_limit(sql, cap=1000)`, the pure
LIMIT-injection function the brief's Outputs section describes living in
app/pipeline/execute_sql.py -- a module that does not exist yet. Written
test-first: this file WILL FAIL WITH ImportError until that module and
function exist, plus (once execute_sql.py exists) until `asyncpg` is
actually installed, since the brief has that module import asyncpg at
module scope. Both failures are expected and correct at this stage.

Extraction of the resulting LIMIT value is done from the rendered SQL
text (via a plain regex) rather than by reaching into sqlglot's internal
AST attribute names, so these tests exercise the function's actual,
observable contract -- the SQL text it hands back for execution -- not
one particular internal representation of it. cap_limit's return value is
accepted as either a raw SQL string or a sqlglot expression object (both
are plausible per the brief's wording); either way it must render, via
`.sql()` or as-is, to text containing the correct LIMIT clause.
"""
import re
import unittest

from app.pipeline.execute_sql import cap_limit
from app.pipeline.validate_sql import SqlValidationError, parse_single_select

_LIMIT_RE = re.compile(r"LIMIT\s+(\d+)", re.IGNORECASE)


def _rendered_sql(result):
    if hasattr(result, "sql"):
        return result.sql(dialect="postgres")
    return result


def _limit_value(result):
    rendered = _rendered_sql(result)
    match = _LIMIT_RE.search(rendered)
    if match is None:
        return None, rendered
    return int(match.group(1)), rendered


class CapLimitTests(unittest.TestCase):
    def test_no_existing_limit_gets_the_cap_added(self):
        sql = "SELECT * FROM olist.orders"
        result = cap_limit(sql, cap=1000)
        value, rendered = _limit_value(result)
        self.assertEqual(
            value,
            1000,
            f"expected a LIMIT of 1000 to be added when none existed, "
            f"got rendered SQL: {rendered!r}",
        )

    def test_a_looser_limit_is_tightened_down_to_the_cap(self):
        sql = "SELECT * FROM olist.orders LIMIT 5000"
        result = cap_limit(sql, cap=1000)
        value, rendered = _limit_value(result)
        self.assertEqual(
            value,
            1000,
            f"expected LIMIT 5000 to be tightened to 1000, got rendered "
            f"SQL: {rendered!r}",
        )

    def test_a_tighter_existing_limit_is_left_untouched(self):
        sql = "SELECT * FROM olist.orders LIMIT 5"
        result = cap_limit(sql, cap=1000)
        value, rendered = _limit_value(result)
        self.assertEqual(
            value,
            5,
            "a tighter existing LIMIT (5) must never be loosened toward "
            f"the cap, got rendered SQL: {rendered!r}",
        )

    def test_default_cap_is_1000_when_not_passed_explicitly(self):
        sql = "SELECT * FROM olist.orders"
        result = cap_limit(sql)
        value, rendered = _limit_value(result)
        self.assertEqual(
            value,
            1000,
            f"expected the default cap to be 1000, got rendered SQL: {rendered!r}",
        )

    def test_the_fixed_questions_real_limit_5_survives_untouched(self):
        # The literal SQL shape produced for FIXED_QUESTION
        # (plans/briefs/2026-08-02-generate-sql.md /
        # tests/test_verify_generate_sql_script.py's ValidateSqlTests),
        # reused here as this brief's own sanity-check reference: "the
        # fixed question's LIMIT 5 must survive untouched".
        sql = (
            "SELECT p.product_category_name, COUNT(DISTINCT oi.order_id) "
            "AS num_orders "
            "FROM olist.order_items oi "
            "JOIN olist.products p ON oi.product_id = p.product_id "
            "GROUP BY p.product_category_name "
            "ORDER BY num_orders DESC "
            "LIMIT 5"
        )
        result = cap_limit(sql, cap=1000)
        value, rendered = _limit_value(result)
        self.assertEqual(
            value,
            5,
            "the fixed question's real LIMIT 5 must survive untouched, "
            f"got rendered SQL: {rendered!r}",
        )

    def test_a_non_literal_limit_expression_is_rejected_with_a_clear_error(self):
        # `LIMIT (SELECT ...)` parses to a Subquery expression, not a
        # plain integer Literal -- cap_limit must fail closed with a
        # message naming the problem rather than raise an uninformative
        # TypeError/AttributeError while comparing it against the cap.
        sql = "SELECT * FROM olist.orders LIMIT (SELECT 5)"
        with self.assertRaises(SqlValidationError) as ctx:
            cap_limit(sql, cap=1000)
        self.assertIn(
            "LIMIT",
            str(ctx.exception),
            f"expected the exception to name the unsupported LIMIT "
            f"expression, got: {ctx.exception}",
        )

    def test_capped_sql_still_parses_as_exactly_one_select_statement(self):
        # Belt-and-suspenders: modifying the parsed statement must not
        # corrupt it into something that is no longer a single, valid
        # SELECT (e.g. accidentally duplicating a clause or emitting a
        # second statement).
        sql = "SELECT * FROM olist.orders LIMIT 5000"
        result = cap_limit(sql, cap=1000)
        rendered = _rendered_sql(result)
        try:
            parse_single_select(rendered)
        except Exception as exc:  # sqlglot's SqlValidationError
            self.fail(
                "expected cap_limit's output to still parse as exactly "
                f"one SELECT statement, but got: {exc}\nrendered SQL: "
                f"{rendered!r}"
            )


if __name__ == "__main__":
    unittest.main()
