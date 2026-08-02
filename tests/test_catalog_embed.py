"""
Integration tests for the pgvector-schema-retrieval brief
(plans/briefs/2026-08-02-pgvector-schema-retrieval.md): `python -m
app.catalog.embed` embeds every `app.catalog_tables` row's `description`
via Voyage AI and upserts one row per table into a new
`app.catalog_embeddings` table, never re-calls Voyage for a table_id
already present there.

Requires: docker compose db service running, the catalog already synced
and described (prior slices), and a working VOYAGE_API_KEY in .env --
these tests make REAL, billed calls to the Voyage AI API the first time
they run against a described-but-not-yet-embedded catalog. Will fail
honestly until app/catalog/embed.py exists.

setUpClass runs sync (idempotent, cheap), then describe (idempotent,
cheap once every table is already described), then embed once. Because
embed.py must skip any table_id already present in
app.catalog_embeddings, this file only ever triggers Voyage calls on the
*first* run against a freshly-described-but-unembedded catalog;
re-running this suite (or the whole tests/ directory) afterwards costs
zero additional Voyage calls, by the same "run once, cached" contract
under test. Per the task setup, all 9 tables are already embedded in the
real dev database, so this suite's own run is expected to skip all 9 and
finish fast, without tripping Voyage's 3 RPM free-tier rate limit.
"""
import unittest
from unittest.mock import patch

from voyageai.error import RateLimitError

from _catalog_helpers import run_sync
from _describe_helpers import run_describe
from _embed_helpers import run_embed, timed_run_embed
from _pg_helpers import get_admin_connection

from app.catalog import embed as embed_module
from app.catalog.embed import EMBEDDING_DIMENSION, embed_text


class CatalogEmbedCliTests(unittest.TestCase):
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

    def setUp(self):
        if self.sync_result.returncode != 0:
            self.fail(
                "python -m app.catalog.sync did not exit 0, so embed.py "
                "has no catalog_tables rows to work with:\n"
                f"stdout={self.sync_result.stdout}\nstderr={self.sync_result.stderr}"
            )
        if self.describe_result.returncode != 0:
            self.fail(
                "python -m app.catalog.describe did not exit 0, so "
                "embed.py has no non-NULL descriptions to embed:\n"
                f"stdout={self.describe_result.stdout}\n"
                f"stderr={self.describe_result.stderr}"
            )

    def test_embed_exits_zero(self):
        self.assertEqual(
            self.embed_result.returncode,
            0,
            "python -m app.catalog.embed did not exit 0:\n"
            f"stdout={self.embed_result.stdout}\n"
            f"stderr={self.embed_result.stderr}",
        )

    def test_every_catalog_table_has_a_matching_embedding_row(self):
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT ct.table_name, ce.table_id "
                "FROM app.catalog_tables ct "
                "LEFT JOIN app.catalog_embeddings ce ON ce.table_id = ct.id "
                "ORDER BY ct.table_name"
            )
            rows = cur.fetchall()
        self.assertEqual(
            len(rows), 9, f"expected 9 catalog_tables rows, found {len(rows)}"
        )
        for table_name, embedded_table_id in rows:
            self.assertIsNotNone(
                embedded_table_id,
                f"olist.{table_name} has no matching app.catalog_embeddings "
                "row after embed.py ran",
            )

    def test_every_embedding_has_the_expected_dimension(self):
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT ct.table_name, vector_dims(ce.embedding) "
                "FROM app.catalog_tables ct "
                "JOIN app.catalog_embeddings ce ON ce.table_id = ct.id "
                "ORDER BY ct.table_name"
            )
            rows = cur.fetchall()
        self.assertEqual(
            len(rows), 9, f"expected 9 embedded tables, found {len(rows)}"
        )
        for table_name, dims in rows:
            self.assertEqual(
                dims,
                EMBEDDING_DIMENSION,
                f"olist.{table_name}'s embedding has {dims} dims, expected "
                f"{EMBEDDING_DIMENSION}",
            )

    def test_second_embed_run_exits_zero_and_leaves_embeddings_unchanged(self):
        # Cast to ::text so the "before"/"after" snapshots compare as
        # plain strings regardless of how psycopg2 would otherwise
        # represent an unregistered pgvector column type.
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT ct.table_name, ce.table_id, ce.embedding::text "
                "FROM app.catalog_tables ct "
                "JOIN app.catalog_embeddings ce ON ce.table_id = ct.id "
                "ORDER BY ct.table_name"
            )
            before = cur.fetchall()

        second_result, elapsed = timed_run_embed()

        self.assertEqual(
            second_result.returncode,
            0,
            "a second python -m app.catalog.embed run (all 9 tables "
            "already embedded) did not exit 0:\n"
            f"stdout={second_result.stdout}\nstderr={second_result.stderr}",
        )

        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT ct.table_name, ce.table_id, ce.embedding::text "
                "FROM app.catalog_tables ct "
                "JOIN app.catalog_embeddings ce ON ce.table_id = ct.id "
                "ORDER BY ct.table_name"
            )
            after = cur.fetchall()
        self.assertEqual(
            before,
            after,
            "embeddings changed on a re-run of embed.py -- an "
            "already-embedded table must never be re-sent to Voyage",
        )

        self.assertLess(
            elapsed,
            60,
            f"a re-run of embed.py against a fully-embedded catalog took "
            f"{elapsed:.1f}s -- long enough to suggest it made real Voyage "
            "API calls instead of skipping already-embedded tables (the "
            "brief requires zero additional Voyage calls on a second run)",
        )


class _FakeEmbeddingsResult:
    def __init__(self, embeddings):
        self.embeddings = embeddings


class _FlakyVoyageClient:
    """Raises RateLimitError a fixed number of times, then succeeds --
    stands in for the real voyageai.Client so embed_text()'s retry/backoff
    logic can be proven without real network calls or waiting out
    Voyage's actual rate-limit window."""

    def __init__(self, failures_before_success):
        self.failures_before_success = failures_before_success
        self.call_count = 0

    def embed(self, texts, model=None, input_type=None):
        self.call_count += 1
        if self.call_count <= self.failures_before_success:
            raise RateLimitError("rate limited (fake)")
        return _FakeEmbeddingsResult([[0.1, 0.2, 0.3]])


class _AlwaysRateLimitedVoyageClient:
    def __init__(self):
        self.call_count = 0

    def embed(self, texts, model=None, input_type=None):
        self.call_count += 1
        raise RateLimitError("rate limited (fake, never recovers)")


class EmbedTextRateLimitRetryTests(unittest.TestCase):
    """Pure unit tests for embed_text()'s retry/backoff -- no network, no
    DB, real Voyage calls entirely replaced by fakes. Proves the retry
    added after this project's real Voyage account tripped its 3 RPM
    free-tier limit during the full test suite run actually recovers
    from a transient RateLimitError, and actually gives up (with a clear
    message) once RATE_LIMIT_MAX_ATTEMPTS is exhausted."""

    def test_recovers_after_fewer_failures_than_the_attempt_cap(self):
        client = _FlakyVoyageClient(
            failures_before_success=embed_module.RATE_LIMIT_MAX_ATTEMPTS - 1
        )
        with patch.object(embed_module.time, "sleep") as mock_sleep:
            result = embed_text(client, "voyage-3.5", "some text", "document")

        self.assertEqual(result, [0.1, 0.2, 0.3])
        self.assertEqual(client.call_count, embed_module.RATE_LIMIT_MAX_ATTEMPTS)
        self.assertEqual(
            mock_sleep.call_count, embed_module.RATE_LIMIT_MAX_ATTEMPTS - 1
        )
        mock_sleep.assert_called_with(embed_module.RATE_LIMIT_RETRY_DELAY_SECONDS)

    def test_raises_a_clear_error_after_the_attempt_cap_is_exhausted(self):
        client = _AlwaysRateLimitedVoyageClient()
        with patch.object(embed_module.time, "sleep") as mock_sleep:
            with self.assertRaises(RuntimeError) as ctx:
                embed_text(client, "voyage-3.5", "some text", "document")

        self.assertEqual(client.call_count, embed_module.RATE_LIMIT_MAX_ATTEMPTS)
        self.assertEqual(
            mock_sleep.call_count, embed_module.RATE_LIMIT_MAX_ATTEMPTS - 1
        )
        self.assertIn(
            f"{embed_module.RATE_LIMIT_MAX_ATTEMPTS} attempts", str(ctx.exception)
        )


if __name__ == "__main__":
    unittest.main()
