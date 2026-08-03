"""
Tests for the eval-harness-v1 brief's `question` parameter requirement
(plans/briefs/2026-08-02-eval-harness-v1.md): to run more than
`FIXED_QUESTION`, `generate_sql()` (app/pipeline/generate_sql.py) and
`get_answer()` (app/pipeline/answer.py) each gain an optional `question`
parameter defaulting to `FIXED_QUESTION`.

The existing test suite (test_generate_sql_cli.py's
GenerateSqlEndToEndTests, test_verify_answer_script.py's
VerifyAnswerDoneCheckTests, both verify_* CLI scripts) already proves the
zero-args default path is unchanged -- that full existing suite passing
unchanged IS this brief's proof for the default path, per its own
Constraints/Done-check wording. This file does not duplicate that; it
covers ONLY:

  (a) a pure, no-network signature check that the `question` parameter
      exists and truly defaults to FIXED_QUESTION (QuestionParameter
      SignatureTests), and
  (b) the non-default path actually works end to end: passing a real,
      different question must produce SQL/rows that genuinely answer
      THAT question, not silently fall back to FIXED_QUESTION regardless
      of what's passed in.

GenerateSqlCustomQuestionEndToEndTests and AnswerCustomQuestionEnd
ToEndTests require: docker compose db service running, the catalog
already synced/described (prior slices), and working
ANTHROPIC_API_KEY/VOYAGE_API_KEY in .env -- each class makes ONE real,
billed Claude API call and ONE real Voyage embedding call in setUpClass,
shared across every test in that class, mirroring test_generate_sql_cli.
py's GenerateSqlEndToEndTests precedent (real end-to-end calls, never
mocked).

Will fail honestly until app/pipeline/generate_sql.py's generate_sql()
and app/pipeline/answer.py's get_answer() both gain the `question`
parameter described above.
"""
import asyncio
import inspect
import unittest

from _catalog_helpers import run_sync
from _describe_helpers import run_describe
from _pg_helpers import get_admin_connection

from app.pipeline import answer, generate_sql

# Deliberately literal and unambiguous ("orders table" names the table
# directly, "how many rows" all but forces a COUNT(*)-shaped query) so
# this test's correctness check doesn't hinge on the LLM's creativity --
# it exists to prove the `question` parameter is real plumbing, not to
# grade SQL-generation quality (that's evals/questions.yaml's job).
CUSTOM_QUESTION = "How many rows are in the orders table?"


class QuestionParameterSignatureTests(unittest.TestCase):
    """Pure, no-network/no-DB checks: no real API calls are needed to
    prove the parameter exists with the right default."""

    def test_generate_sql_has_a_question_parameter_defaulting_to_fixed_question(self):
        sig = inspect.signature(generate_sql.generate_sql)
        self.assertIn(
            "question",
            sig.parameters,
            "generate_sql() has no 'question' parameter -- the brief "
            "requires one, defaulting to FIXED_QUESTION",
        )
        self.assertEqual(
            sig.parameters["question"].default,
            generate_sql.FIXED_QUESTION,
            "generate_sql()'s 'question' parameter must default to "
            "FIXED_QUESTION, so every existing zero-args caller keeps its "
            "exact current behavior",
        )

    def test_get_answer_has_a_question_parameter_defaulting_to_fixed_question(self):
        sig = inspect.signature(answer.get_answer)
        self.assertIn(
            "question",
            sig.parameters,
            "get_answer() has no 'question' parameter -- the brief "
            "requires one, defaulting to FIXED_QUESTION",
        )
        self.assertEqual(
            sig.parameters["question"].default,
            generate_sql.FIXED_QUESTION,
            "get_answer()'s 'question' parameter must default to "
            "FIXED_QUESTION, so every existing zero-args caller keeps its "
            "exact current behavior",
        )


class GenerateSqlCustomQuestionEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sync_result = run_sync()
        cls.describe_result = run_describe()
        cls.sql = None
        if cls.sync_result.returncode == 0 and cls.describe_result.returncode == 0:
            # One real Claude API call plus one real Voyage embedding
            # call, shared across every test in this class.
            cls.sql = generate_sql.generate_sql(question=CUSTOM_QUESTION)

    def setUp(self):
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

    def test_generate_sql_accepts_a_non_default_question_and_returns_a_select(self):
        self.assertIsInstance(self.sql, str)
        self.assertTrue(
            self.sql.strip().upper().startswith("SELECT"),
            f"generate_sql(question=...) did not return a SELECT "
            f"statement for the custom question: {self.sql!r}",
        )

    def test_generate_sql_for_the_custom_question_references_the_orders_table(self):
        self.assertIn(
            "orders",
            self.sql.lower(),
            "generate_sql(question='How many rows are in the orders "
            f"table?') did not reference the orders table: {self.sql!r}",
        )

    def test_generate_sql_for_the_custom_question_does_not_answer_the_fixed_question(
        self,
    ):
        # Proves the question parameter actually changed what the LLM was
        # asked, rather than silently ignoring it and answering
        # FIXED_QUESTION ("top 5 product categories by number of orders")
        # regardless of what's passed in.
        self.assertNotIn(
            "product_category_name",
            self.sql.lower(),
            "generate_sql(question=<a different question>) produced SQL "
            "that still answers FIXED_QUESTION -- the question parameter "
            f"does not appear to be threaded through: {self.sql!r}",
        )


class AnswerCustomQuestionEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sync_result = run_sync()
        cls.describe_result = run_describe()
        cls.sql = None
        cls.rows = None
        cls.real_order_count = None
        if cls.sync_result.returncode == 0 and cls.describe_result.returncode == 0:
            # One real Claude API call (via generate_sql), one real
            # Voyage embedding call, and one real execute against the
            # read-only asyncpg connection -- shared across every test in
            # this class.
            cls.sql, cls.rows = asyncio.run(
                answer.get_answer(question=CUSTOM_QUESTION)
            )

            # Independently, real ground truth queried directly (never
            # hardcoded) so the correctness check below survives a future
            # reseed with a different row count.
            conn = get_admin_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM olist.orders")
                    cls.real_order_count = cur.fetchone()[0]
            finally:
                conn.close()

    def setUp(self):
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

    def test_get_answer_accepts_a_non_default_question_and_returns_a_select(self):
        self.assertIsInstance(self.sql, str)
        self.assertTrue(
            self.sql.strip().upper().startswith("SELECT"),
            f"get_answer(question=...) did not produce a SELECT "
            f"statement for the custom question: {self.sql!r}",
        )

    def test_get_answer_for_the_custom_question_does_not_answer_the_fixed_question(
        self,
    ):
        self.assertNotIn(
            "product_category_name",
            self.sql.lower(),
            "get_answer(question=<a different question>) produced SQL "
            "that still answers FIXED_QUESTION -- the question parameter "
            f"does not appear to be threaded through: {self.sql!r}",
        )

    def test_get_answer_for_the_custom_question_returns_the_real_orders_row_count(
        self,
    ):
        self.assertIsNotNone(
            self.rows,
            "get_answer(question=...) returned no rows (a prior "
            "sync/describe step must have failed)",
        )
        self.assertEqual(
            len(self.rows),
            1,
            "expected exactly one aggregate row for 'how many rows are "
            f"in the orders table?', got: {self.rows!r}",
        )
        (returned_value,) = self.rows[0].values()
        self.assertEqual(
            int(returned_value),
            self.real_order_count,
            "get_answer(question='How many rows are in the orders "
            f"table?') returned {returned_value!r}, but the real, live "
            f"olist.orders row count is {self.real_order_count!r} -- the "
            "custom question was not actually answered correctly",
        )


if __name__ == "__main__":
    unittest.main()
