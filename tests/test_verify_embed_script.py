"""
The pgvector-schema-retrieval brief's done-check ingredient
(plans/briefs/2026-08-02-pgvector-schema-retrieval.md): `python -m
app.catalog.verify_embed` exits 0 only if every one of the 9
`catalog_tables` rows has a matching `app.catalog_embeddings` row whose
vector has the expected dimension.

Runs the exact CLI command via subprocess, mirroring
test_verify_describe_script.py's convention. Depends on a prior
`python -m app.catalog.sync` + `python -m app.catalog.describe` +
`python -m app.catalog.embed` having already populated embeddings --
embed.py's own "run once, cached" behavior means calling it again here
triggers zero additional Voyage calls once any prior test/run has already
embedded all 9 tables. Will fail honestly until
app/catalog/verify_embed.py exists.
"""
import unittest

from _catalog_helpers import run_sync
from _describe_helpers import run_describe
from _embed_helpers import run_embed, run_verify_embed
from _pg_helpers import get_admin_connection


class VerifyEmbedDoneCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sync_result = run_sync()
        cls.describe_result = run_describe()
        cls.embed_result = run_embed()
        cls.conn = get_admin_connection()
        cls.conn.autocommit = True

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "conn", None) is not None:
            cls.conn.close()

    def _require_embedded_catalog(self):
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
        if self.embed_result.returncode != 0:
            self.fail(
                "python -m app.catalog.embed did not exit 0, so "
                "verify_embed cannot be exercised against a fully "
                f"embedded catalog:\nstdout={self.embed_result.stdout}\n"
                f"stderr={self.embed_result.stderr}"
            )

    def test_verify_embed_exits_zero_against_an_embedded_catalog(self):
        self._require_embedded_catalog()

        result = run_verify_embed()
        self.assertEqual(
            result.returncode,
            0,
            "python -m app.catalog.verify_embed did not exit 0 against a "
            "fully-embedded catalog (the brief's done-check ingredient):\n"
            f"stdout={result.stdout}\nstderr={result.stderr}",
        )

    def test_verify_embed_stdout_reports_a_pass_style_marker(self):
        self._require_embedded_catalog()

        result = run_verify_embed()
        self.assertIn(
            "PASS",
            result.stdout.upper(),
            "expected a PASS-style marker in verify_embed stdout, matching "
            f"the verify_sync.py/verify_describe.py convention:\n"
            f"stdout={result.stdout}",
        )

    def test_verify_embed_fails_when_an_embedding_is_missing(self):
        # Behavioral proof the done-check actually validates every row,
        # not just an always-pass script: delete one embedding row and
        # confirm verify_embed catches it, then restore it immediately so
        # no other test (or a future test run) sees a missing row and
        # re-triggers a real Voyage call for that table.
        self._require_embedded_catalog()

        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT ce.table_id, ce.embedding::text "
                "FROM app.catalog_embeddings ce "
                "JOIN app.catalog_tables ct ON ct.id = ce.table_id "
                "ORDER BY ct.table_name LIMIT 1"
            )
            table_id, original_embedding_text = cur.fetchone()

        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM app.catalog_embeddings WHERE table_id = %s",
                    (table_id,),
                )

            result = run_verify_embed()
            self.assertNotEqual(
                result.returncode,
                0,
                "python -m app.catalog.verify_embed unexpectedly exited 0 "
                "with one app.catalog_embeddings row deleted -- the "
                "done-check must actually validate every row:\n"
                f"stdout={result.stdout}",
            )
        finally:
            with self.conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO app.catalog_embeddings (table_id, embedding) "
                    "VALUES (%s, %s::vector)",
                    (table_id, original_embedding_text),
                )


if __name__ == "__main__":
    unittest.main()
