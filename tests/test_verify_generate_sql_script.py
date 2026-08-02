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

ValidateSqlTests is the sqlglot-based validator's unit-level coverage
(plans/briefs/2026-08-02-validate-sql.md): direct calls into
app.pipeline.validate_sql's parse_single_select/check_table_references/
check_column_references against hand-built fake schema dicts, no DB
cursor and no API calls required. It replaced the prior slice's
hand-rolled regex tokenizer (check_references) and its dedicated test
class, now that the sqlglot validator is proven equivalent-or-better on
the same hallucinated-table/hallucinated-column scenarios.

Will fail honestly until app/pipeline/verify_generate_sql.py exists.
"""
import unittest

from _catalog_helpers import run_sync
from _describe_helpers import run_describe
from _generate_sql_helpers import run_verify_generate_sql
from sqlglot import exp

from app.pipeline.validate_sql import (
    SqlValidationError,
    check_column_references,
    check_table_references,
    parse_single_select,
)


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


class ValidateSqlTests(unittest.TestCase):
    """Direct, hand-built unit tests for the sqlglot-based validator
    (plans/briefs/2026-08-02-validate-sql.md): no DB cursor and no API
    calls, exercising parse_single_select/check_table_references/
    check_column_references directly against hand-built SQL strings and a
    hand-built fake per-table schema dict (the shape fetch_catalog_schema
    is meant to return, so these functions can be tested without a live
    app.catalog_tables/app.catalog_columns query). The fixed question's
    real generated-SQL shape, a multi-statement string, a non-SELECT
    statement, a hallucinated table name, and a hallucinated column name
    are the four deliberately-invalid scenarios the brief's done-check
    calls out by name; a trailing-semicolon and a CTE-name case are added
    because the brief explicitly describes both as things the parser must
    NOT misclassify as a second statement or an unknown table,
    respectively.
    """

    SCHEMA = {
        "order_items": {"order_id": "TEXT", "product_id": "TEXT"},
        "products": {"product_id": "TEXT", "product_category_name": "TEXT"},
    }

    FIXED_QUESTION_SQL = (
        "SELECT p.product_category_name, COUNT(DISTINCT oi.order_id) AS num_orders "
        "FROM olist.order_items oi "
        "JOIN olist.products p ON oi.product_id = p.product_id "
        "GROUP BY p.product_category_name "
        "ORDER BY num_orders DESC "
        "LIMIT 5"
    )

    def test_the_real_fixed_question_sql_passes_parse_table_and_column_checks(self):
        statement = parse_single_select(self.FIXED_QUESTION_SQL)
        try:
            check_table_references(statement, set(self.SCHEMA))
            check_column_references(statement, self.SCHEMA)
        except SqlValidationError as exc:
            self.fail(
                "expected the fixed question's real generated SQL to pass "
                f"validation with no exception, but got: {exc}"
            )

    def test_a_multi_statement_string_is_rejected_by_parse_single_select(self):
        sql = "SELECT * FROM olist.products; DROP TABLE olist.products;"
        with self.assertRaises(SqlValidationError) as ctx:
            parse_single_select(sql)
        message = str(ctx.exception).lower()
        self.assertIn(
            "statement",
            message,
            "expected the exception message to mention the statement "
            f"count problem, got: {ctx.exception}",
        )

    def test_a_non_select_statement_is_rejected_by_parse_single_select(self):
        sql = "DELETE FROM olist.products"
        with self.assertRaises(SqlValidationError) as ctx:
            parse_single_select(sql)
        message = str(ctx.exception).lower()
        self.assertIn(
            "select",
            message,
            "expected the exception message to name that the statement "
            f"isn't a SELECT, got: {ctx.exception}",
        )

    def test_a_hallucinated_table_name_is_rejected_by_check_table_references(self):
        sql = "SELECT nt.order_id FROM olist.nonexistent_table nt"
        statement = parse_single_select(sql)
        with self.assertRaises(SqlValidationError) as ctx:
            check_table_references(statement, set(self.SCHEMA))
        self.assertIn(
            "nonexistent_table",
            str(ctx.exception),
            "expected the exception message to name the hallucinated "
            f"table, got: {ctx.exception}",
        )

    def test_a_hallucinated_column_name_is_rejected_by_check_column_references(self):
        sql = "SELECT p.totally_made_up_column FROM olist.products p"
        statement = parse_single_select(sql)

        # table-check must pass first: "products" is a real table, only
        # the column is invented.
        try:
            check_table_references(statement, set(self.SCHEMA))
        except SqlValidationError as exc:
            self.fail(
                "expected the table check to pass for a real table with "
                f"only a hallucinated column, but got: {exc}"
            )

        with self.assertRaises(SqlValidationError) as ctx:
            check_column_references(statement, self.SCHEMA)
        self.assertIn(
            "totally_made_up_column",
            str(ctx.exception),
            "expected the exception message to name the hallucinated "
            f"column, got: {ctx.exception}",
        )

    def test_a_trailing_semicolon_alone_is_not_a_second_statement(self):
        sql = "SELECT * FROM olist.products;"
        try:
            statement = parse_single_select(sql)
        except SqlValidationError as exc:
            self.fail(
                "a lone trailing semicolon must not be treated as a "
                f"second statement, but parse_single_select raised: {exc}"
            )
        self.assertIsInstance(
            statement,
            exp.Select,
            f"expected a single parsed SELECT expression, got: {statement!r}",
        )

    def test_a_wrong_schema_qualifier_is_rejected_even_if_the_table_basename_is_real(
        self,
    ):
        # "products" is a real table name, but only under olist -- a
        # reference to it under any other schema must still be rejected,
        # not waved through because the bare basename happens to match.
        sql = "SELECT * FROM pg_catalog.products"
        statement = parse_single_select(sql)
        with self.assertRaises(SqlValidationError) as ctx:
            check_table_references(statement, set(self.SCHEMA))
        self.assertIn(
            "pg_catalog.products",
            str(ctx.exception),
            "expected the exception message to name the wrongly-qualified "
            f"table reference, got: {ctx.exception}",
        )

    def test_a_differently_cased_table_or_cte_name_is_not_wrongly_flagged_as_unknown(
        self,
    ):
        # Postgres folds unquoted identifiers to lowercase, so
        # olist.PRODUCTS and a CTE named RECENT referenced as "recent" are
        # both real, valid references -- the qualifier check already
        # normalizes case, so name/CTE-name matching must too, or a valid
        # reference could be spuriously rejected as "unknown".
        statement = parse_single_select("SELECT * FROM olist.PRODUCTS")
        try:
            check_table_references(statement, set(self.SCHEMA))
        except SqlValidationError as exc:
            self.fail(
                "a differently-cased but real table name must not be "
                f"rejected as unknown, but got: {exc}"
            )

        cte_statement = parse_single_select(
            "WITH RECENT AS (SELECT product_id FROM olist.products) "
            "SELECT * FROM recent"
        )
        try:
            check_table_references(cte_statement, {"products"})
        except SqlValidationError as exc:
            self.fail(
                "a case-mismatched CTE name/reference pair must still "
                f"resolve to the CTE, not an unknown table, but got: {exc}"
            )

    def test_a_table_valued_function_call_is_rejected_with_a_specific_message(self):
        # A table-valued function call (e.g. generate_series) also parses
        # as exp.Table but with an empty .name -- the rejection message
        # must still name the actual problem, not read as a bare "olist.".
        sql = "SELECT * FROM generate_series(1, 10) AS t(n)"
        statement = parse_single_select(sql)
        with self.assertRaises(SqlValidationError) as ctx:
            check_table_references(statement, set(self.SCHEMA))
        message = str(ctx.exception)
        self.assertIn(
            "generate_series",
            message.lower(),
            "expected the exception message to name the table-valued "
            f"function call instead of a bare 'olist.', got: {message}",
        )

    def test_a_catalog_only_qualifier_is_rejected_the_same_as_a_schema_qualifier(
        self,
    ):
        # sqlglot's "catalog..table" double-dot form leaves .db empty and
        # puts the qualifying text in .catalog instead -- a schema-only
        # check would treat this identically to a bare, unqualified
        # reference and wrongly allow it. Both qualifier fields must be
        # checked, combined, so this is rejected the same way
        # pg_catalog.products is.
        sql = "SELECT * FROM pg_catalog..products"
        statement = parse_single_select(sql)
        with self.assertRaises(SqlValidationError) as ctx:
            check_table_references(statement, set(self.SCHEMA))
        self.assertIn(
            "pg_catalog.products",
            str(ctx.exception),
            "expected the exception message to name the wrongly-qualified "
            f"table reference, got: {ctx.exception}",
        )

    def test_a_cte_name_does_not_mask_a_schema_qualified_reference_to_the_same_name(
        self,
    ):
        # A CTE is only ever addressed unqualified. A CTE named "products"
        # must not exempt a *schema-qualified* reference to "products"
        # elsewhere in the same query -- that can never actually be the
        # CTE, and letting it through would mask a real cross-schema leak.
        sql = (
            "WITH products AS (SELECT 1 AS x) "
            "SELECT * FROM pg_catalog.products"
        )
        statement = parse_single_select(sql)
        with self.assertRaises(SqlValidationError) as ctx:
            check_table_references(statement, {"products"})
        self.assertIn(
            "pg_catalog.products",
            str(ctx.exception),
            "expected the exception message to name the wrongly-qualified "
            f"reference despite the same-named CTE, got: {ctx.exception}",
        )

    def test_a_cte_name_is_not_mistaken_for_an_unknown_table(self):
        sql = (
            "WITH recent AS (SELECT product_id FROM olist.products) "
            "SELECT * FROM recent"
        )
        statement = parse_single_select(sql)
        try:
            check_table_references(statement, {"products"})
        except SqlValidationError as exc:
            self.fail(
                "a CTE's own name ('recent') is not a catalog table and "
                f"must not be flagged as an unknown table reference: {exc}"
            )


if __name__ == "__main__":
    unittest.main()
