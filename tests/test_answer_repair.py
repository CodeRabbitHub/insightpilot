"""
Tests for the repair-loop brief (plans/briefs/2026-08-03-repair-loop.md):
`app.pipeline.answer.get_answer()` gains one-shot repair-on-failure
orchestration through a new internal `async def
_answer_with_repair(question, sql)` -- per the brief's Gate-1 resolution,
"the exact function get_answer() calls after generate_sql() returns: it
tries validate+execute on sql, and on any exception calls repair_sql()
once and retries validate+execute on the repaired SQL, letting a second
failure propagate unmodified."

This file calls `_answer_with_repair()` directly with a real question and
a real, hand-crafted, deliberately-broken SQL string (a real olist table,
a nonexistent column -- same fixture shape as test_repair_sql.py's, kept
independent per-file rather than shared, matching this repo's existing
per-test-file constant convention e.g. test_question_parameter.py's
CUSTOM_QUESTION), proving the seam get_answer() itself calls actually
fires the repair path and succeeds, with no mocking and no dependency on
the LLM failing to produce valid SQL on its own first try.

Separately, RetryOnceTests proves the brief's "a second failure
propagates unmodified" claim deterministically, without mocking anything:
`_answer_with_repair()` delegates its try/repair-once/propagate shape to
a new `_retry_once(attempt, recover)` helper that has no I/O of its own
(no DB, no LLM) -- it just calls the two callables it's given. That makes
it possible to prove real propagation semantics with plain, real Python
functions standing in for `attempt`/`recover`, the same way
`execute_sql.py`'s `cap_limit()` is unit-tested directly rather than only
through a live DB round-trip.

Requires: docker compose db service running, the catalog already synced
and described (prior slices), and working ANTHROPIC_API_KEY/
VOYAGE_API_KEY in .env -- _answer_with_repair() makes ONE real, billed
Anthropic call (via repair_sql()) plus one real asyncpg execute against
the read-only connection, shared across every test in
AnswerWithRepairEndToEndTests via setUpClass, never repeated per-test.

Will fail honestly until app/pipeline/answer.py's _answer_with_repair()
and app/pipeline/repair_sql.py's repair_sql() both exist.
"""
import asyncio
import inspect
import unittest

from _catalog_helpers import run_sync
from _describe_helpers import run_describe

from app.pipeline import answer

QUESTION = "How many rows are in the orders table?"

# Real table (olist.orders), fake column -- passes validate_sql()'s
# table-reference check but fails its real column-reference check, so
# _answer_with_repair()'s first validate+execute attempt genuinely fails
# and the repair path must fire for real, not be short-circuited by a
# no-op success.
BROKEN_SQL = "SELECT nonexistent_col_for_answer_repair_test FROM olist.orders"


class AnswerWithRepairSignatureTests(unittest.TestCase):
    """Pure, no-network checks: _answer_with_repair() exists with the
    exact shape the brief's Gate-1 resolution names, and get_answer()'s
    own source really does call it (the brief's explicit orchestration
    seam), independent of what any real call returns."""

    def test_answer_with_repair_is_an_async_function_of_question_and_sql(self):
        self.assertTrue(
            asyncio.iscoroutinefunction(answer._answer_with_repair),
            "app.pipeline.answer._answer_with_repair must be an async "
            "function per the brief's Gate-1 resolution",
        )
        sig = inspect.signature(answer._answer_with_repair)
        self.assertEqual(
            list(sig.parameters),
            ["question", "sql"],
            "_answer_with_repair() must accept exactly (question, sql) "
            f"per the brief's Gate-1 resolution, got {list(sig.parameters)!r}",
        )

    def test_get_answer_actually_calls_answer_with_repair(self):
        source = inspect.getsource(answer.get_answer)
        self.assertIn(
            "_answer_with_repair",
            source,
            "get_answer() must call the new _answer_with_repair() seam "
            "per the brief's Gate-1 resolution -- its source does not "
            f"reference it:\n{source}",
        )

    def test_answer_with_repair_delegates_to_retry_once(self):
        source = inspect.getsource(answer._answer_with_repair)
        self.assertIn(
            "_retry_once",
            source,
            "_answer_with_repair() must delegate its try/repair-once/"
            "propagate shape to _retry_once() so that shape is testable "
            f"without mocking -- its source does not reference it:\n{source}",
        )


class RetryOnceTests(unittest.TestCase):
    """Pure, no-network, no-DB, no-LLM tests of _retry_once(attempt,
    recover) -- the control-flow shape _answer_with_repair() delegates
    to. Proves the brief's "a second failure propagates unmodified"
    claim deterministically: attempt/recover here are plain real
    functions, not mocks of any real dependency, because _retry_once
    itself performs no I/O -- it only calls the two callables it's
    given."""

    def test_retry_once_returns_the_first_attempts_result_when_it_succeeds(self):
        async def attempt():
            return "first-result"

        async def recover(exc):
            self.fail("recover() must not run when attempt() succeeds")

        result = asyncio.run(answer._retry_once(attempt, recover))
        self.assertEqual(result, "first-result")

    def test_retry_once_calls_recover_with_the_first_exception_and_returns_its_result(
        self,
    ):
        first_error = ValueError("first failure")

        async def attempt():
            raise first_error

        async def recover(exc):
            self.assertIs(
                exc,
                first_error,
                "recover() must be called with the exact exception attempt() "
                "raised",
            )
            return "recovered-result"

        result = asyncio.run(answer._retry_once(attempt, recover))
        self.assertEqual(result, "recovered-result")

    def test_retry_once_propagates_a_second_failure_unmodified(self):
        # The exact claim the brief and app/pipeline/answer.py's
        # docstring make: "letting a second failure propagate
        # unmodified" -- if recover() also raises, that second
        # exception must surface from _retry_once(), not be swallowed
        # or replaced.
        second_error = RuntimeError("second failure")

        async def attempt():
            raise ValueError("first failure")

        async def recover(exc):
            raise second_error

        with self.assertRaises(RuntimeError) as ctx:
            asyncio.run(answer._retry_once(attempt, recover))
        self.assertIs(
            ctx.exception,
            second_error,
            "a second failure from recover() must propagate as the exact "
            "same exception object, unmodified -- not wrapped, not "
            "swallowed, not replaced by the first exception",
        )

    def test_retry_once_never_calls_recover_before_attempt_fails(self):
        calls = []

        async def attempt():
            calls.append("attempt")
            raise ValueError("x")

        async def recover(exc):
            calls.append("recover")
            return "ok"

        asyncio.run(answer._retry_once(attempt, recover))
        self.assertEqual(
            calls,
            ["attempt", "recover"],
            "recover() must only run after attempt() fails, exactly once",
        )


class AnswerWithRepairEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sync_result = run_sync()
        cls.describe_result = run_describe()
        cls.result = None
        cls.error = None
        if cls.sync_result.returncode == 0 and cls.describe_result.returncode == 0:
            try:
                # One real, billed Anthropic call (via repair_sql(),
                # inside _answer_with_repair) plus one real asyncpg
                # execute -- shared across every test in this class.
                cls.result = asyncio.run(
                    answer._answer_with_repair(QUESTION, BROKEN_SQL)
                )
            except Exception as exc:  # noqa: BLE001 -- captured, not swallowed
                cls.error = exc

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

    def test_answer_with_repair_does_not_raise_for_the_handcrafted_broken_sql(self):
        self.assertIsNone(
            self.error,
            "_answer_with_repair(question, broken_sql) raised instead of "
            "self-correcting via one repair attempt: "
            f"{self.error!r}",
        )

    def test_answer_with_repair_returns_a_sql_and_rows_pair(self):
        self.assertIsNotNone(
            self.result,
            "_answer_with_repair() produced no result (a prior "
            "sync/describe step must have failed, or it raised -- see "
            "the other test in this class)",
        )
        self.assertEqual(
            len(self.result),
            2,
            "expected _answer_with_repair() to return a (sql, rows) "
            f"pair, got: {self.result!r}",
        )

    def test_answer_with_repair_returns_a_different_sql_than_the_broken_input(self):
        returned_sql, _rows = self.result
        self.assertIsInstance(returned_sql, str)
        self.assertNotEqual(
            returned_sql.strip().rstrip(";").strip().lower(),
            BROKEN_SQL.strip().rstrip(";").strip().lower(),
            "_answer_with_repair() returned the same broken SQL back "
            "unchanged -- the repair path does not appear to have fired",
        )

    def test_answer_with_repair_returns_a_select_statement(self):
        returned_sql, _rows = self.result
        self.assertTrue(
            returned_sql.strip().upper().startswith("SELECT"),
            f"expected the repaired SQL to be a SELECT statement, got: "
            f"{returned_sql!r}",
        )

    def test_answer_with_repair_returns_real_nonempty_rows(self):
        _sql, rows = self.result
        self.assertIsNotNone(rows)
        self.assertGreater(
            len(rows),
            0,
            "expected _answer_with_repair() to return at least one real "
            f"row after repairing and executing the SQL, got: {rows!r}",
        )


if __name__ == "__main__":
    unittest.main()
