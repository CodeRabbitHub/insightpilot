"""
Integration + unit tests for the generate-sql-from-a-fixed-question brief
(plans/briefs/2026-08-02-generate-sql.md): for the one hardcoded question,
`app.pipeline.generate_sql.generate_sql()` builds the full olist catalog
as schema context, makes a single Claude API call, validates the
response's `{"sql": "..."}` shape through a Pydantic model that only
accepts SELECT statements, and returns the raw SQL string (it must not
print -- the CLI's `main()` does that).

Extended by plans/briefs/2026-08-02-pgvector-schema-retrieval.md:
`build_schema_context()` no longer builds context from every olist table
-- a new `retrieve_relevant_tables()` embeds the fixed question via
Voyage AI and runs a pgvector top-k similarity search against
`app.catalog_embeddings`, so schema context now comes from a real subset
of the catalog, not a hardcoded full-table list.

GenerateSqlEndToEndTests requires: docker compose db service running, the
catalog already synced, described, and embedded (prior slices), and
working ANTHROPIC_API_KEY/VOYAGE_API_KEY in .env -- generate_sql() makes
REAL, billed calls to both the Anthropic and Voyage APIs every time it
runs (there is no "already done" cache like describe.py's/embed.py's for
generate_sql() itself), so the one shared call made in setUpClass is
reused across every test in that class. The retrieval-only test below
reuses that same setUpClass state rather than making its own extra
Voyage call, respecting this project's Voyage account's 3 RPM free-tier
rate limit.

GenerateSqlModuleConstantsTests and GenerateSqlResponseValidatorTests are
pure unit tests: no network or DB calls, independent of whatever the LLM
actually returns.

Will fail honestly until app/pipeline/generate_sql.py (and its Pydantic
response model) exist.
"""
import unittest

import pydantic
import voyageai

from _catalog_helpers import run_sync
from _describe_helpers import run_describe
from _pg_helpers import get_admin_connection, olist_table_names

from app.catalog.sync import require_env
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
        cls.retrieved_tables = None
        if cls.sync_result.returncode == 0 and cls.describe_result.returncode == 0:
            # One real Claude API call (plus one real Voyage call for the
            # fixed question's own embedding, inside generate_sql()),
            # shared across every test in this class so the suite doesn't
            # re-bill either API per assertion.
            cls.sql = generate_sql.generate_sql()

            # One additional, shared Voyage call to exercise
            # retrieve_relevant_tables() directly (generate_sql() above
            # only returns the final SQL string, not the retrieved table
            # list) -- reused by every test needing it, never repeated
            # per-test, to respect the 3 RPM free-tier rate limit.
            voyage_client = voyageai.Client(api_key=require_env("VOYAGE_API_KEY"))
            conn = get_admin_connection()
            try:
                with conn.cursor() as cur:
                    cls.retrieved_tables = generate_sql.retrieve_relevant_tables(
                        cur, voyage_client, generate_sql.FIXED_QUESTION
                    )
            finally:
                conn.close()

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

    def test_retrieve_relevant_tables_returns_a_real_subset_not_the_full_catalog(self):
        # Per the pgvector-schema-retrieval brief: retrieval must return a
        # genuine top-k subset, never a hardcoded full-table-list check.
        # We only assert it's fewer than all 9 tables (proving it's
        # actually top-k retrieval) and that the two tables the fixed
        # question needs (order_items for order counts, products for
        # category names) rank in that subset.
        conn = get_admin_connection()
        try:
            with conn.cursor() as cur:
                total_table_count = len(olist_table_names(cur))
        finally:
            conn.close()
        self.assertEqual(
            total_table_count, 9, f"expected 9 olist tables, found {total_table_count}"
        )

        self.assertIsNotNone(
            self.retrieved_tables,
            "retrieve_relevant_tables() was not exercised in setUpClass "
            "(a prior sync/describe step must have failed)",
        )
        retrieved_table_names = {
            table_name for _table_id, table_name, _description, _ddl_summary
            in self.retrieved_tables
        }

        self.assertLess(
            len(retrieved_table_names),
            total_table_count,
            f"retrieve_relevant_tables() returned {len(retrieved_table_names)} "
            f"tables out of {total_table_count} -- expected a genuine top-k "
            "subset, not the full catalog",
        )
        self.assertIn(
            "order_items",
            retrieved_table_names,
            f"retrieve_relevant_tables() did not include order_items in its "
            f"top-k result for the fixed question: {retrieved_table_names}",
        )
        self.assertIn(
            "products",
            retrieved_table_names,
            f"retrieve_relevant_tables() did not include products in its "
            f"top-k result for the fixed question: {retrieved_table_names}",
        )


if __name__ == "__main__":
    unittest.main()
