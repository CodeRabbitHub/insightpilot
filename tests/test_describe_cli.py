"""
Integration tests for the llm-table-descriptions brief
(plans/briefs/2026-08-02-llm-table-descriptions.md): `python -m
app.catalog.describe` generates and persists a one-paragraph LLM
description into each of the 9 `app.catalog_tables` rows, never
re-calls the LLM for a table that already has one, and never touches
out-of-scope tables (`app.kb_chunks`, `app.catalog_columns`'s shape).

Requires: docker compose db service running, the catalog already synced
(prior slice), and a working ANTHROPIC_API_KEY in .env -- these tests
make REAL, billed calls to the Anthropic API the first time they run
against a freshly-synced (all-NULL) catalog. Will fail honestly until
app/catalog/describe.py (and its Pydantic response model) exist.

setUpClass runs sync once (idempotent, cheap) then describe once. Because
describe.py must skip any table whose description is already non-NULL,
this file only ever triggers LLM calls on the *first* run against a
freshly-synced catalog; re-running this suite (or the whole tests/
directory) afterwards costs zero additional LLM calls, by the same
"run once, cached" contract under test.

Note: the brief's "if the retry also fails for a table, the run fails
loudly" constraint is not exercised here -- forcing a genuine Pydantic
validation failure would require mocking the Anthropic response, which
this project's convention (real infrastructure, no mocks) rules out for
these integration tests.
"""
import unittest

from _catalog_helpers import run_sync
from _describe_helpers import run_describe, timed_run_describe
from _pg_helpers import get_admin_connection


class DescribeCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sync_result = run_sync()
        cls.describe_result = run_describe()
        cls.conn = get_admin_connection()
        cls.conn.autocommit = True

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "conn", None) is not None:
            cls.conn.close()

    def setUp(self):
        if self.sync_result.returncode != 0:
            self.fail(
                "python -m app.catalog.sync did not exit 0, so describe.py "
                "has no catalog_tables rows to work with:\n"
                f"stdout={self.sync_result.stdout}\nstderr={self.sync_result.stderr}"
            )

    def test_describe_exits_zero(self):
        self.assertEqual(
            self.describe_result.returncode,
            0,
            "python -m app.catalog.describe did not exit 0:\n"
            f"stdout={self.describe_result.stdout}\n"
            f"stderr={self.describe_result.stderr}",
        )

    def test_every_catalog_table_gets_a_non_null_description(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT table_name, description FROM app.catalog_tables")
            rows = cur.fetchall()
        self.assertEqual(
            len(rows), 9, f"expected 9 catalog_tables rows, found {len(rows)}"
        )
        for table_name, description in rows:
            self.assertIsNotNone(
                description,
                f"description is NULL for {table_name} after describe.py ran",
            )

    def test_descriptions_read_as_genuine_paragraphs_not_stubs(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT table_name, description FROM app.catalog_tables")
            rows = cur.fetchall()
        for table_name, description in rows:
            with self.subTest(table=table_name):
                stripped = description.strip()
                self.assertTrue(stripped, f"description is blank for {table_name}")
                word_count = len(stripped.split())
                self.assertGreaterEqual(
                    word_count,
                    20,
                    f"description for {table_name} is only {word_count} "
                    f"words, too short to be a genuine paragraph: {stripped!r}",
                )
                sentence_count = sum(stripped.count(ch) for ch in ".!?")
                self.assertGreaterEqual(
                    sentence_count,
                    2,
                    f"description for {table_name} does not read as "
                    f"multiple sentences: {stripped!r}",
                )

    def test_descriptions_are_distinct_per_table(self):
        # A real per-table description should differ table to table; all
        # nine being identical would indicate a stub/placeholder was
        # written instead of a genuine per-table LLM response.
        with self.conn.cursor() as cur:
            cur.execute("SELECT description FROM app.catalog_tables")
            descriptions = [row[0] for row in cur.fetchall()]
        self.assertEqual(
            len(set(descriptions)),
            len(descriptions),
            f"expected 9 distinct descriptions, found duplicates: {descriptions}",
        )

    def test_second_describe_run_exits_zero_and_leaves_descriptions_unchanged(self):
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT table_name, description FROM app.catalog_tables "
                "ORDER BY table_name"
            )
            before = cur.fetchall()

        second_result, elapsed = timed_run_describe()

        self.assertEqual(
            second_result.returncode,
            0,
            "a second python -m app.catalog.describe run (all 9 tables "
            "already described) did not exit 0:\n"
            f"stdout={second_result.stdout}\nstderr={second_result.stderr}",
        )

        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT table_name, description FROM app.catalog_tables "
                "ORDER BY table_name"
            )
            after = cur.fetchall()
        self.assertEqual(
            before,
            after,
            "descriptions changed on a re-run of describe.py -- an "
            "already-described table must never be re-sent to the LLM",
        )

        self.assertLess(
            elapsed,
            60,
            f"a re-run of describe.py against a fully-described catalog "
            f"took {elapsed:.1f}s -- long enough to suggest it made real "
            "LLM calls instead of skipping already-described tables (the "
            "brief requires zero additional LLM calls on a second run)",
        )

    def test_sync_after_describe_does_not_null_out_descriptions(self):
        # The done-check's third clause, exercised against real
        # describe.py-generated descriptions (not hand-set SQL text) --
        # distinct from test_catalog_sync.py's
        # test_sync_preserves_an_existing_description_across_a_resync,
        # which covers the same UPSERT mechanism with an arbitrary value.
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT table_name, description FROM app.catalog_tables "
                "ORDER BY table_name"
            )
            before = cur.fetchall()
        for table_name, description in before:
            self.assertIsNotNone(
                description,
                f"precondition failed: {table_name} has no description yet",
            )

        resync_result = run_sync()
        self.assertEqual(
            resync_result.returncode,
            0,
            "python -m app.catalog.sync did not exit 0 after descriptions "
            f"already existed:\nstdout={resync_result.stdout}\n"
            f"stderr={resync_result.stderr}",
        )

        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT table_name, description FROM app.catalog_tables "
                "ORDER BY table_name"
            )
            after = cur.fetchall()
        self.assertEqual(
            before,
            after,
            "python -m app.catalog.sync reset one or more descriptions "
            "back to NULL (or changed them) after they already existed",
        )

    def test_describe_does_not_create_a_kb_chunks_table(self):
        # Out-of-scope per the brief: "no embeddings/pgvector writes to
        # kb_chunks (M3 scope)". A conforming describe.py never needs to
        # create that table at all in this slice.
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_name = 'kb_chunks'"
            )
            count = cur.fetchone()[0]
        self.assertEqual(
            count,
            0,
            "an app.kb_chunks (or similarly named) table exists -- "
            "embeddings/pgvector writes are out of scope for this slice",
        )

    def test_catalog_columns_shape_is_unchanged(self):
        # Out-of-scope per the brief: "any change to ... the shape of
        # catalog_columns". Shape per PRD.md's schema section (id,
        # table_id, column_name, data_type, is_pk, is_fk, ref_table,
        # sample_values_json).
        expected_columns = {
            "id",
            "table_id",
            "column_name",
            "data_type",
            "is_pk",
            "is_fk",
            "ref_table",
            "sample_values_json",
        }
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'app' AND table_name = 'catalog_columns'"
            )
            actual_columns = {row[0] for row in cur.fetchall()}
        self.assertEqual(
            actual_columns,
            expected_columns,
            "app.catalog_columns's column shape changed -- out of scope "
            "for this slice",
        )


if __name__ == "__main__":
    unittest.main()
