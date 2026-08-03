"""
Integration tests for the glossary-retrieval brief
(plans/briefs/2026-08-03-glossary-retrieval.md): `python -m
app.glossary.embed` chunks glossary.md by `## ` heading, embeds each
chunk's content via Voyage AI, and upserts one row per chunk into a new
`app.kb_chunks(id, source, content, embedding vector(1024))` table, never
re-calling Voyage for a `source` already present there.

Requires: docker compose db service running and a working VOYAGE_API_KEY
in .env -- these tests make REAL, billed calls to the Voyage AI API the
first time they run against a not-yet-embedded glossary.md. Will fail
honestly until app/glossary/embed.py exists.

setUpClass runs the glossary embed script once. Because embed.py must
skip any `source` already present in app.kb_chunks, this file only ever
triggers Voyage calls on the *first* run against a fresh, unembedded
glossary; re-running this suite (or the whole tests/ directory)
afterwards costs zero additional Voyage calls, by the same "run once,
cached" contract under test -- mirroring test_catalog_embed.py's
precedent exactly for the new app/glossary/ package.
"""
import unittest

from _glossary_helpers import run_glossary_embed, timed_run_glossary_embed
from _pg_helpers import REPO_ROOT, get_admin_connection

GLOSSARY_FILE = REPO_ROOT / "glossary.md"


def _live_expected_sources():
    from app.glossary.embed import parse_glossary_entries

    text = GLOSSARY_FILE.read_text(encoding="utf-8")
    return {entry[0] for entry in parse_glossary_entries(text)}


class GlossaryEmbedSchemaDdlUnitTests(unittest.TestCase):
    """Pure unit tests for SCHEMA_DDL's text -- no network, no DB. Proves
    the Constraints' explicit dimension callout: 1024, not the PRD's
    predates-Voyage 1536."""

    def test_schema_ddl_creates_the_expected_kb_chunks_table_name(self):
        from app.glossary.embed import SCHEMA_DDL

        self.assertIn(
            "kb_chunks",
            SCHEMA_DDL,
            "SCHEMA_DDL does not create an app.kb_chunks table by that name",
        )

    def test_schema_ddl_uses_1024_dimensions_not_the_prds_1536(self):
        from app.glossary.embed import SCHEMA_DDL

        self.assertIn(
            "vector(1024)",
            SCHEMA_DDL,
            "SCHEMA_DDL must declare embedding vector(1024) -- Voyage's "
            "real, already-proven output size -- not the PRD's stale 1536",
        )
        self.assertNotIn(
            "1536",
            SCHEMA_DDL,
            "SCHEMA_DDL still references the PRD's predates-Voyage 1536 "
            "dimension -- must be 1024 per app.catalog.embed's "
            "EMBEDDING_DIMENSION",
        )

    def test_schema_ddl_declares_the_expected_columns(self):
        from app.glossary.embed import SCHEMA_DDL

        for column in ("id", "source", "content", "embedding"):
            with self.subTest(column=column):
                self.assertIn(
                    column,
                    SCHEMA_DDL,
                    f"SCHEMA_DDL does not appear to declare a '{column}' column",
                )

    def test_reuses_catalog_embeds_voyage_model_and_dimension_constants(self):
        # Constraint: "Reuse the exact same Voyage AI embeddings
        # provider, voyage-3.5 model ... no new provider, no reinvented
        # retry logic." Checked as value equality against
        # app.catalog.embed's already-proven constants (not a new,
        # independently-defined 1024/voyage-3.5 in the glossary module).
        from app.catalog.embed import EMBEDDING_DIMENSION as catalog_dim
        from app.catalog.embed import VOYAGE_MODEL as catalog_model
        from app.glossary.embed import EMBEDDING_DIMENSION as glossary_dim
        from app.glossary.embed import VOYAGE_MODEL as glossary_model

        self.assertEqual(glossary_model, catalog_model)
        self.assertEqual(glossary_dim, catalog_dim)

    def test_reuses_catalog_embeds_embed_text_function_directly(self):
        # Stronger than value equality: proves embed_text itself is
        # imported/reused, not a reinvented copy that happens to look
        # similar (the brief's "no reinvented retry logic" constraint).
        from app.catalog.embed import embed_text as catalog_embed_text
        from app.glossary.embed import embed_text as glossary_embed_text

        self.assertIs(
            glossary_embed_text,
            catalog_embed_text,
            "app.glossary.embed.embed_text is not the same function object "
            "as app.catalog.embed.embed_text -- the brief requires reusing "
            "embed_text()'s existing rate-limit retry, never reinventing it",
        )


class GlossaryEmbedCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.embed_result = run_glossary_embed()
        cls.conn = get_admin_connection()
        cls.conn.autocommit = True

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "conn", None) is not None:
            cls.conn.close()

    def test_embed_exits_zero(self):
        self.assertEqual(
            self.embed_result.returncode,
            0,
            "python -m app.glossary.embed did not exit 0:\n"
            f"stdout={self.embed_result.stdout}\nstderr={self.embed_result.stderr}",
        )

    def test_kb_chunks_table_has_the_expected_column_shape(self):
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'app' AND table_name = 'kb_chunks'"
            )
            actual_columns = {row[0] for row in cur.fetchall()}
        self.assertEqual(
            actual_columns,
            {"id", "source", "content", "embedding"},
            "app.kb_chunks does not have the expected (id, source, "
            f"content, embedding) column shape, found: {actual_columns}",
        )

    def test_every_parsed_glossary_entry_has_a_matching_kb_chunks_row(self):
        expected_sources = _live_expected_sources()
        self.assertGreater(
            len(expected_sources),
            1,
            "parse_glossary_entries() produced no usable sources to check "
            "app.kb_chunks against",
        )

        with self.conn.cursor() as cur:
            cur.execute("SELECT source FROM app.kb_chunks")
            actual_sources = {row[0] for row in cur.fetchall()}

        missing = expected_sources - actual_sources
        self.assertFalse(
            missing,
            f"app.kb_chunks is missing rows for these glossary sources "
            f"after embed.py ran: {missing}",
        )
        self.assertEqual(
            len(actual_sources),
            len(expected_sources),
            f"app.kb_chunks has {len(actual_sources)} distinct sources, "
            f"expected exactly {len(expected_sources)} (one per parsed "
            "glossary entry, no extras/duplicates)",
        )

    def test_every_kb_chunks_embedding_has_the_expected_dimension(self):
        from app.glossary.embed import EMBEDDING_DIMENSION

        with self.conn.cursor() as cur:
            cur.execute("SELECT source, vector_dims(embedding) FROM app.kb_chunks")
            rows = cur.fetchall()
        self.assertGreater(len(rows), 0, "app.kb_chunks has no rows to check")
        for source, dims in rows:
            with self.subTest(source=source):
                self.assertEqual(
                    dims,
                    EMBEDDING_DIMENSION,
                    f"kb_chunks row {source!r} has {dims} dims, expected "
                    f"{EMBEDDING_DIMENSION}",
                )

    def test_second_embed_run_exits_zero_and_leaves_kb_chunks_unchanged(self):
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT source, content, embedding::text FROM app.kb_chunks "
                "ORDER BY source"
            )
            before = cur.fetchall()

        second_result, elapsed = timed_run_glossary_embed()

        self.assertEqual(
            second_result.returncode,
            0,
            "a second python -m app.glossary.embed run (every chunk "
            "already embedded) did not exit 0:\n"
            f"stdout={second_result.stdout}\nstderr={second_result.stderr}",
        )

        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT source, content, embedding::text FROM app.kb_chunks "
                "ORDER BY source"
            )
            after = cur.fetchall()
        self.assertEqual(
            before,
            after,
            "app.kb_chunks changed on a re-run of embed.py -- an "
            "already-embedded chunk (by its stable source key) must "
            "never be re-sent to Voyage",
        )

        self.assertLess(
            elapsed,
            60,
            f"a re-run of embed.py against a fully-embedded glossary took "
            f"{elapsed:.1f}s -- long enough to suggest it made real Voyage "
            "API calls instead of skipping already-embedded chunks",
        )


if __name__ == "__main__":
    unittest.main()
