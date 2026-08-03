"""
Tests for the repair-loop brief (plans/briefs/2026-08-03-repair-loop.md):
a new `app.pipeline.repair_sql.repair_sql(question, failed_sql,
error_message)` takes the original question, a SQL string that failed
validation (or execution), and the real error message, and returns a
corrected SQL string via one real Anthropic call (reusing the existing
`GenerateSqlResponse` Pydantic model, per the brief's Constraints).

This file proves repair_sql() alone self-corrects: a real, hand-crafted
SQL string against a real olist table (`orders`) but a nonexistent column
is real, table-check-passing SQL that is fed through the real,
already-shipped validate_sql() gate to capture ITS real
SqlValidationError message (never a canned/hardcoded error string), then
repair_sql() is called for real with that question/sql/error triple. The
returned SQL must differ from the broken input and must itself pass a
fresh, real validate_sql() call.

Requires: docker compose db service running, the catalog already synced
and described (prior slices), and a working ANTHROPIC_API_KEY in .env --
repair_sql() makes ONE real, billed Claude API call, shared across every
test in RepairSqlEndToEndTests via setUpClass (mirrors
test_question_parameter.py's GenerateSqlCustomQuestionEndToEndTests
precedent: one real call per class, never repeated per-test).

Will fail honestly until app/pipeline/repair_sql.py's repair_sql() and
prompts/repair_sql.md both exist.
"""
import inspect
import unittest

from _catalog_helpers import run_sync
from _describe_helpers import run_describe
from _pg_helpers import REPO_ROOT, get_admin_connection

from app.pipeline.validate_sql import SqlValidationError, validate_sql

QUESTION = "How many rows are in the orders table?"

# Real table (olist.orders, seeded in every prior slice), fake column --
# passes validate_sql()'s table-reference check but fails its real
# column-reference check (app/pipeline/validate_sql.py's
# check_column_references, via sqlglot's qualify()), so the captured
# error below is genuine, not synthesized.
BROKEN_SQL = "SELECT nonexistent_column_xyz FROM olist.orders"


def _capture_real_validation_error(sql):
    conn = get_admin_connection()
    try:
        with conn.cursor() as cur:
            validate_sql(sql, cur)
    finally:
        conn.close()


class RepairSqlPromptFileTests(unittest.TestCase):
    """Pure, no-network check: prompts/repair_sql.md exists as a real,
    non-blank, versioned repo file (the brief's Outputs/Constraints:
    string.Template-based like prompts/generate_sql.md, never an inline
    string)."""

    def test_repair_sql_prompt_file_exists_and_is_non_blank(self):
        prompt_path = REPO_ROOT / "prompts" / "repair_sql.md"
        self.assertTrue(
            prompt_path.exists(),
            f"expected {prompt_path} to exist per the brief's Outputs "
            "(a new prompts/repair_sql.md)",
        )
        self.assertTrue(
            prompt_path.read_text(encoding="utf-8").strip(),
            f"{prompt_path} exists but is blank",
        )


class RepairSqlSignatureTests(unittest.TestCase):
    """Pure, no-network check: repair_sql() has the exact signature the
    brief's Gate-1 resolution names, independent of what any real call
    returns."""

    def test_repair_sql_has_the_gate_1_signature(self):
        from app.pipeline import repair_sql

        sig = inspect.signature(repair_sql.repair_sql)
        self.assertEqual(
            list(sig.parameters),
            ["question", "failed_sql", "error_message"],
            "repair_sql() must accept exactly (question, failed_sql, "
            "error_message) per the brief's Gate-1 resolution, got "
            f"{list(sig.parameters)!r}",
        )


class RepairSqlEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sync_result = run_sync()
        cls.describe_result = run_describe()
        cls.captured_error = None
        cls.repaired_sql = None
        if cls.sync_result.returncode == 0 and cls.describe_result.returncode == 0:
            try:
                _capture_real_validation_error(BROKEN_SQL)
            except SqlValidationError as exc:
                cls.captured_error = str(exc)

            if cls.captured_error is not None:
                from app.pipeline.repair_sql import repair_sql

                # One real, billed Anthropic call, shared across every
                # test in this class -- never repeated per-test.
                cls.repaired_sql = repair_sql(
                    QUESTION, BROKEN_SQL, cls.captured_error
                )

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
        if self.captured_error is None:
            self.fail(
                "validate_sql() did not raise SqlValidationError for the "
                f"deliberately-broken test SQL {BROKEN_SQL!r} -- the "
                "hand-crafted fixture no longer fails validation, so this "
                "test class can't prove repair_sql() self-corrects anything"
            )

    def test_the_handcrafted_sql_really_does_fail_real_column_validation(self):
        # Guards the fixture itself (using validate_sql.py's own literal
        # "unknown column referenced: ..." wording, per its source):
        # if this ever stops raising for this reason, the rest of this
        # class would be vacuously "passing" for the wrong reason.
        self.assertIn(
            "unknown column referenced",
            self.captured_error.lower(),
            "expected the real SqlValidationError to be the column-"
            f"reference check, got: {self.captured_error!r}",
        )

    def test_repair_sql_returns_a_nonblank_string(self):
        self.assertIsInstance(self.repaired_sql, str)
        self.assertTrue(
            self.repaired_sql.strip(), "repair_sql() returned a blank string"
        )

    def test_repair_sql_returns_a_different_sql_string_than_the_broken_input(self):
        self.assertNotEqual(
            self.repaired_sql.strip().rstrip(";").strip().lower(),
            BROKEN_SQL.strip().rstrip(";").strip().lower(),
            "repair_sql() returned the same broken SQL back unchanged -- "
            "it must produce a corrected SELECT, not echo the input",
        )

    def test_repair_sql_output_passes_a_fresh_real_validate_sql_call(self):
        conn = get_admin_connection()
        try:
            with conn.cursor() as cur:
                try:
                    validate_sql(self.repaired_sql, cur)
                except SqlValidationError as exc:
                    self.fail(
                        "repair_sql()'s output did not pass a fresh, "
                        f"real validate_sql() call: {exc}\nrepaired sql: "
                        f"{self.repaired_sql!r}"
                    )
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
