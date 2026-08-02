"""
Integration + unit tests for the generate-sql-from-a-fixed-question brief
(plans/briefs/2026-08-02-generate-sql.md): for the one hardcoded question,
`app.pipeline.generate_sql.generate_sql()` builds the full olist catalog
as schema context, makes a single Claude API call, validates the
response's `{"sql": "..."}` shape through a Pydantic model that only
accepts SELECT statements, and returns the raw SQL string (it must not
print -- the CLI's `main()` does that).

GenerateSqlEndToEndTests requires: docker compose db service running, the
catalog already synced and described (prior slices), and a working
ANTHROPIC_API_KEY in .env -- generate_sql() makes a REAL, billed call to
the Anthropic API every time it runs (there is no "already done" cache
like describe.py's), so the one call made in setUpClass is shared across
every test in that class.

GenerateSqlModuleConstantsTests and GenerateSqlResponseValidatorTests are
pure unit tests: no network or DB calls, independent of whatever the LLM
actually returns.

Will fail honestly until app/pipeline/generate_sql.py (and its Pydantic
response model) exist.
"""
import unittest

import pydantic

from _catalog_helpers import run_sync
from _describe_helpers import run_describe
from _pg_helpers import get_admin_connection, olist_table_names

from app.pipeline import generate_sql


class GenerateSqlModuleConstantsTests(unittest.TestCase):
    def test_fixed_question_matches_the_brief_exactly(self):
        self.assertEqual(
            generate_sql.FIXED_QUESTION,
            "What are the top 5 product categories by number of orders?",
        )

    def test_max_retries_matches_the_describe_py_pattern(self):
        # describe.py's call_llm_for_description uses MAX_RETRIES = 1;
        # the brief requires generate_sql.py to match that pattern
        # exactly (one retry, wrapping the whole attempt).
        self.assertEqual(generate_sql.MAX_RETRIES, 1)


class GenerateSqlResponseValidatorTests(unittest.TestCase):
    """Pure unit tests for GenerateSqlResponse -- prove the Pydantic model
    gives the retry loop real teeth by rejecting non-SELECT SQL,
    independent of what the LLM actually returns."""

    def test_accepts_a_real_select_statement(self):
        response = generate_sql.GenerateSqlResponse(
            sql=(
                "SELECT product_category_name, COUNT(*) AS order_count "
                "FROM olist.order_items GROUP BY product_category_name"
            )
        )
        self.assertTrue(response.sql.strip().upper().startswith("SELECT"))

    def test_accepts_lowercase_select_case_insensitively(self):
        response = generate_sql.GenerateSqlResponse(sql="select 1")
        self.assertTrue(response.sql.strip().upper().startswith("SELECT"))

    def test_tolerates_a_trailing_semicolon_and_whitespace(self):
        # Per the approved plan: the validator strips a trailing
        # semicolon/whitespace before checking the SELECT prefix, so this
        # construction must not raise.
        generate_sql.GenerateSqlResponse(sql="  SELECT 1;  ")

    def test_rejects_a_drop_table_statement(self):
        with self.assertRaises(pydantic.ValidationError):
            generate_sql.GenerateSqlResponse(sql="DROP TABLE olist.orders")

    def test_rejects_a_non_select_statement_referencing_a_real_table(self):
        with self.assertRaises(pydantic.ValidationError):
            generate_sql.GenerateSqlResponse(
                sql="DELETE FROM olist.orders WHERE order_id = '1'"
            )

    def test_rejects_a_blank_sql_string(self):
        with self.assertRaises(pydantic.ValidationError):
            generate_sql.GenerateSqlResponse(sql="   ")


class GenerateSqlEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sync_result = run_sync()
        cls.describe_result = run_describe()
        cls.sql = None
        if cls.sync_result.returncode == 0 and cls.describe_result.returncode == 0:
            # One real Claude API call, shared across every test in this
            # class so the suite doesn't re-bill the API per assertion.
            cls.sql = generate_sql.generate_sql()

    def setUp(self):
        if self.sync_result.returncode != 0:
            self.fail(
                "python -m app.catalog.sync did not exit 0, so "
                "generate_sql() has no catalog to build schema context "
                f"from:\nstdout={self.sync_result.stdout}\n"
                f"stderr={self.sync_result.stderr}"
            )
        if self.describe_result.returncode != 0:
            self.fail(
                "python -m app.catalog.describe did not exit 0:\n"
                f"stdout={self.describe_result.stdout}\n"
                f"stderr={self.describe_result.stderr}"
            )

    def test_generate_sql_returns_a_nonempty_string(self):
        self.assertIsInstance(self.sql, str)
        self.assertTrue(self.sql.strip(), "generate_sql() returned a blank string")

    def test_generate_sql_returns_a_select_statement(self):
        self.assertTrue(
            self.sql.strip().upper().startswith("SELECT"),
            f"generate_sql() did not return a SELECT statement: {self.sql!r}",
        )

    def test_build_schema_context_covers_all_nine_tables(self):
        conn = get_admin_connection()
        try:
            with conn.cursor() as cur:
                table_names = olist_table_names(cur)
                self.assertEqual(
                    len(table_names),
                    9,
                    f"expected 9 olist tables, found {len(table_names)}",
                )
                context = generate_sql.build_schema_context(cur)
        finally:
            conn.close()

        self.assertIsInstance(context, str)
        for table_name in table_names:
            self.assertIn(
                f"olist.{table_name}",
                context,
                f"build_schema_context() output is missing olist.{table_name}",
            )


if __name__ == "__main__":
    unittest.main()
