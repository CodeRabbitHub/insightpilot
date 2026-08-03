"""
The glossary-retrieval brief's verify-CLI ingredient
(plans/briefs/2026-08-03-glossary-retrieval.md): `python -m
app.glossary.verify_embed` exits 0 only if every parsed glossary.md entry
has a matching `app.kb_chunks` row whose vector has the expected
dimension -- mirroring `app/catalog/verify_embed.py`'s convention and
test_verify_embed_script.py's test shape exactly, for the new
`app/glossary/` package.

Depends on a prior `python -m app.glossary.embed` having already
populated app.kb_chunks -- embed.py's own "run once, cached" behavior
means calling it again here triggers zero additional Voyage calls once
any prior test/run has already embedded every glossary chunk. Will fail
honestly until app/glossary/verify_embed.py exists.
"""
import unittest

from _glossary_helpers import run_glossary_embed, run_glossary_verify_embed
from _pg_helpers import (
    acquire_advisory_lock,
    get_admin_connection,
    release_advisory_lock,
)

_MISSING_KB_CHUNK_LOCK_KEY = "insightpilot-test-verify-embed-missing-kb-chunk"


class GlossaryVerifyEmbedDoneCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = get_admin_connection()
        # addClassCleanup, not tearDownClass: unittest skips tearDownClass
        # entirely if setUpClass raises, which would leak both the open
        # connection and, worse, the advisory lock below for the rest of
        # this process's lifetime (it's session-scoped, released only by
        # an explicit unlock or the session ending) -- exactly the stall
        # this fix exists to prevent. Cleanups still run on a setUpClass
        # failure, and in reverse (LIFO) order, so the lock (added second)
        # releases before the connection (added first) closes.
        cls.addClassCleanup(cls.conn.close)
        cls.conn.autocommit = True
        # Acquired before run_glossary_embed() below, not after: embed()
        # re-embeds (and inserts over) any source it finds missing from
        # app.kb_chunks, so if this ran unlocked, a concurrent process's
        # racy test holding the lock mid-deletion could have its missing
        # row silently restored by this process's own setup before that
        # process ever gets to check it. Held for this class's entire run,
        # not just the mutating test below, for the same reason: the other
        # two tests here assert a fully-embedded glossary, which that test
        # transiently violates.
        acquire_advisory_lock(cls.conn, _MISSING_KB_CHUNK_LOCK_KEY)
        cls.addClassCleanup(
            release_advisory_lock, cls.conn, _MISSING_KB_CHUNK_LOCK_KEY
        )
        cls.embed_result = run_glossary_embed()

    def _require_embedded_glossary(self):
        if self.embed_result.returncode != 0:
            self.fail(
                "python -m app.glossary.embed did not exit 0, so "
                "verify_embed cannot be exercised against a fully "
                f"embedded glossary:\nstdout={self.embed_result.stdout}\n"
                f"stderr={self.embed_result.stderr}"
            )

    def test_verify_embed_exits_zero_against_an_embedded_glossary(self):
        self._require_embedded_glossary()

        result = run_glossary_verify_embed()
        self.assertEqual(
            result.returncode,
            0,
            "python -m app.glossary.verify_embed did not exit 0 against a "
            "fully-embedded glossary (the brief's done-check ingredient):\n"
            f"stdout={result.stdout}\nstderr={result.stderr}",
        )

    def test_verify_embed_stdout_reports_a_pass_style_marker(self):
        self._require_embedded_glossary()

        result = run_glossary_verify_embed()
        self.assertIn(
            "PASS",
            result.stdout.upper(),
            "expected a PASS-style marker in verify_embed stdout, matching "
            f"app.catalog.verify_embed's convention:\nstdout={result.stdout}",
        )

    def test_verify_embed_fails_when_a_kb_chunk_is_missing(self):
        # Behavioral proof the done-check actually validates every row,
        # not just an always-pass script: delete one kb_chunks row and
        # confirm verify_embed catches it, then restore it immediately so
        # no other test (or a future test run) sees a missing row and
        # re-triggers a real Voyage call for that chunk.
        self._require_embedded_glossary()

        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, source, content, embedding::text FROM app.kb_chunks "
                "ORDER BY source LIMIT 1"
            )
            row = cur.fetchone()
        self.assertIsNotNone(
            row, "app.kb_chunks has no rows to exercise this test against"
        )
        chunk_id, source, content, embedding_text = row

        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM app.kb_chunks WHERE id = %s", (chunk_id,))

            result = run_glossary_verify_embed()
            self.assertNotEqual(
                result.returncode,
                0,
                "python -m app.glossary.verify_embed unexpectedly exited 0 "
                "with one app.kb_chunks row deleted -- the done-check "
                "must actually validate every row:\n"
                f"stdout={result.stdout}",
            )
        finally:
            with self.conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO app.kb_chunks (id, source, content, embedding) "
                    "VALUES (%s, %s, %s, %s::vector)",
                    (chunk_id, source, content, embedding_text),
                )


if __name__ == "__main__":
    unittest.main()
