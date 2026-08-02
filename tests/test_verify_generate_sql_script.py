"""
The generate-sql-from-a-fixed-question brief's literal done-check
(plans/briefs/2026-08-02-generate-sql.md): `python -m
app.pipeline.verify_generate_sql` exits 0 only if the fixed question
produces a printed SQL string starting with SELECT (case-insensitive)
and every table/column identifier it references is confirmed present in
a live query against app.catalog_tables/app.catalog_columns.

VerifyGenerateSqlDoneCheckTests requires: docker compose db service
running, the catalog already synced and described, and a working
ANTHROPIC_API_KEY in .env -- it makes a REAL, billed call to the
Anthropic API via generate_sql() (no "already done" cache exists for
this slice).

CheckReferencesTests is pure unit-level: no API or DB calls, exercising
the alias-aware regex tokenizer described in the approved plan directly
against hand-built SQL strings and a hand-built fake catalog. This is
called out as the brief's trickiest logic (a hand-rolled tokenizer, not
sqlglot) so it gets the most direct scrutiny here rather than relying
only on the end-to-end pass/fail above. Forcing a genuine end-to-end
*failure* of the CLI (e.g. a hallucinated table) would require mocking
the Anthropic response, which this project's convention (real
infrastructure, no mocks) rules out -- matching test_verify_describe_
script.py's equivalent note for describe.py's retry-failure path.

Will fail honestly until app/pipeline/verify_generate_sql.py (and its
check_references function) exist.
"""
import unittest

from _catalog_helpers import run_sync
from _describe_helpers import run_describe
from _generate_sql_helpers import run_verify_generate_sql

from app.pipeline import verify_generate_sql


class VerifyGenerateSqlDoneCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sync_result = run_sync()
        cls.describe_result = run_describe()

    def _require_described_catalog(self):
        if self.sync_result.returncode != 0:
            self.fail(
                "python -m app.catalog.sync did not exit 0:\n"
                f"stdout={self.sync_result.stdout}\nstderr={self.sync_result.stderr}"
            )
        if self.describe_result.returncode != 0:
            self.fail(
                "python -m app.catalog.describe did not exit 0, so "
                "verify_generate_sql cannot be exercised against a "
                f"fully-described catalog:\nstdout={self.describe_result.stdout}\n"
                f"stderr={self.describe_result.stderr}"
            )

    def test_verify_generate_sql_exits_zero_for_the_fixed_question(self):
        self._require_described_catalog()

        result = run_verify_generate_sql()
        self.assertEqual(
            result.returncode,
            0,
            "python -m app.pipeline.verify_generate_sql did not exit 0 "
            f"for the fixed question (the brief's done-check):\n"
            f"stdout={result.stdout}\nstderr={result.stderr}",
        )

    def test_verify_generate_sql_stdout_reports_the_passed_marker(self):
        self._require_described_catalog()

        result = run_verify_generate_sql()
        self.assertIn(
            "verify_generate_sql: PASSED",
            result.stdout,
            "expected the exact 'verify_generate_sql: PASSED' marker in "
            f"stdout:\nstdout={result.stdout}",
        )


class CheckReferencesTests(unittest.TestCase):
    """Direct, hand-built unit tests for the alias-aware reference
    checker described in the approved plan: strip string literals, match
    olist.<table> and <alias>.<column> dotted pairs, collect AS-aliases
    and FROM/JOIN implicit aliases, then confirm any remaining bare
    identifier is a known table or column name. valid_tables/valid_columns
    are hand-built fakes here (not a live DB query) so this class can run
    with no infrastructure at all, per the brief's emphasis that this
    tokenizer logic deserves the most direct unit-level scrutiny."""

    VALID_TABLES = {"orders", "order_items", "products", "customers"}
    VALID_COLUMNS = {
        "order_id",
        "product_id",
        "customer_id",
        "product_category_name",
        "price",
        "order_status",
    }

    def test_passes_a_query_with_table_and_output_aliases(self):
        sql = (
            "SELECT p.product_category_name, COUNT(*) AS order_count "
            "FROM olist.order_items oi "
            "JOIN olist.products p ON oi.product_id = p.product_id "
            "GROUP BY p.product_category_name "
            "ORDER BY order_count DESC "
            "LIMIT 5"
        )
        failures = verify_generate_sql.check_references(
            sql, self.VALID_TABLES, self.VALID_COLUMNS
        )
        self.assertFalse(
            failures,
            f"expected no failures for a valid aliased query, got {failures}",
        )

    def test_passes_a_query_with_where_clause_alias_column_reference(self):
        sql = (
            "SELECT c.customer_id, COUNT(*) AS order_count "
            "FROM olist.orders o "
            "JOIN olist.customers c ON o.customer_id = c.customer_id "
            "WHERE o.order_status = 'delivered' "
            "GROUP BY c.customer_id"
        )
        failures = verify_generate_sql.check_references(
            sql, self.VALID_TABLES, self.VALID_COLUMNS
        )
        self.assertFalse(
            failures,
            f"expected no failures for a valid alias.column WHERE clause, "
            f"got {failures}",
        )

    def test_ignores_identifier_look_alikes_inside_string_literals(self):
        sql = (
            "SELECT o.order_status FROM olist.orders o "
            "WHERE o.order_status = 'olist.not_a_real_table'"
        )
        failures = verify_generate_sql.check_references(
            sql, self.VALID_TABLES, self.VALID_COLUMNS
        )
        self.assertFalse(
            failures,
            "a fake dotted identifier inside a string literal should "
            f"never be treated as a real reference, got {failures}",
        )

    def test_does_not_false_positive_on_sql_keywords_and_aggregate_functions(self):
        sql = (
            "SELECT p.product_category_name, COUNT(*) AS order_count "
            "FROM olist.order_items oi "
            "JOIN olist.products p ON oi.product_id = p.product_id "
            "GROUP BY p.product_category_name "
            "HAVING COUNT(*) > 10 "
            "ORDER BY order_count DESC, p.product_category_name ASC "
            "LIMIT 5"
        )
        failures = verify_generate_sql.check_references(
            sql, self.VALID_TABLES, self.VALID_COLUMNS
        )
        self.assertFalse(
            failures,
            "SQL keywords/aggregate functions must not be treated as "
            f"unknown identifiers, got {failures}",
        )

    def test_fails_on_a_hallucinated_table_name(self):
        sql = (
            "SELECT * FROM olist.nonexistent_table nt "
            "JOIN olist.orders o ON nt.order_id = o.order_id"
        )
        failures = verify_generate_sql.check_references(
            sql, self.VALID_TABLES, self.VALID_COLUMNS
        )
        self.assertTrue(failures, "expected a failure for a hallucinated table name")
        self.assertIn("nonexistent_table", str(failures))

    def test_fails_on_a_hallucinated_column_name(self):
        sql = "SELECT p.totally_made_up_column FROM olist.products p"
        failures = verify_generate_sql.check_references(
            sql, self.VALID_TABLES, self.VALID_COLUMNS
        )
        self.assertTrue(failures, "expected a failure for a hallucinated column name")
        self.assertIn("totally_made_up_column", str(failures))


if __name__ == "__main__":
    unittest.main()
