"""
Tests for the glossary-retrieval brief's pipeline change
(plans/briefs/2026-08-03-glossary-retrieval.md):
`app.pipeline.generate_sql` gains `retrieve_relevant_glossary_entries(cur,
voyage_client, question, k=...)`, analogous to the existing
`retrieve_relevant_tables()`, run against the new `app.kb_chunks` table.

Per the brief's own precedent (the pgvector-schema-retrieval slice's
test_generate_sql_cli.py): retrieval must be proven as a genuine top-k
subset of the glossary, never a hardcoded full-list/full-count check.

GlossaryRetrievalSignatureTests is a pure, no-network check of the
function's shape. GlossaryRetrievalEndToEndTests requires: docker compose
db service running, glossary.md already embedded into app.kb_chunks
(app/glossary/embed.py, exercised here via setUpClass), and a working
VOYAGE_API_KEY in .env -- retrieve_relevant_glossary_entries() makes ONE
real, billed Voyage embedding call for the fixed question, shared across
every test in this class (mirroring test_generate_sql_cli.py's
GenerateSqlEndToEndTests convention). No Claude call is made here --
proving retrieval alone doesn't require billing the more expensive LLM
call.

Will fail honestly until app/glossary/embed.py and
app.pipeline.generate_sql.retrieve_relevant_glossary_entries() exist.
"""
import inspect
import unittest

import voyageai

from _glossary_helpers import run_glossary_embed
from _pg_helpers import get_admin_connection

from app.catalog.sync import require_env
from app.pipeline import generate_sql


class GlossaryRetrievalSignatureTests(unittest.TestCase):
    """Pure, no-network/no-DB check: the brief names this function and
    its parameters explicitly."""

    def test_retrieve_relevant_glossary_entries_has_the_expected_parameters(self):
        sig = inspect.signature(generate_sql.retrieve_relevant_glossary_entries)
        for param_name in ("cur", "voyage_client", "question", "k"):
            with self.subTest(param=param_name):
                self.assertIn(
                    param_name,
                    sig.parameters,
                    "retrieve_relevant_glossary_entries() is missing the "
                    f"'{param_name}' parameter the brief names explicitly",
                )

    def test_k_parameter_has_a_default(self):
        sig = inspect.signature(generate_sql.retrieve_relevant_glossary_entries)
        self.assertIsNot(
            sig.parameters["k"].default,
            inspect.Parameter.empty,
            "retrieve_relevant_glossary_entries()'s 'k' parameter has no "
            "default -- the brief's 'k=...' signature implies one, "
            "mirroring retrieve_relevant_tables()'s RETRIEVAL_K default",
        )


class GlossaryRetrievalEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.embed_result = run_glossary_embed()
        cls.retrieved = None
        cls.total_kb_chunk_count = None
        if cls.embed_result.returncode == 0:
            conn = get_admin_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM app.kb_chunks")
                    cls.total_kb_chunk_count = cur.fetchone()[0]

                    # One real, shared Voyage call for the fixed
                    # question's embedding -- reused by every test in
                    # this class to respect the 3 RPM free-tier limit.
                    voyage_client = voyageai.Client(
                        api_key=require_env("VOYAGE_API_KEY")
                    )
                    cls.retrieved = generate_sql.retrieve_relevant_glossary_entries(
                        cur, voyage_client, generate_sql.FIXED_QUESTION
                    )
            finally:
                conn.close()

    def setUp(self):
        if self.embed_result.returncode != 0:
            self.fail(
                "python -m app.glossary.embed did not exit 0, so "
                "retrieve_relevant_glossary_entries() has no app.kb_chunks "
                f"rows to search:\nstdout={self.embed_result.stdout}\n"
                f"stderr={self.embed_result.stderr}"
            )
        self.assertIsNotNone(
            self.retrieved,
            "retrieve_relevant_glossary_entries() was not exercised in "
            "setUpClass",
        )

    def test_returns_a_nonempty_result(self):
        self.assertGreater(
            len(self.retrieved),
            0,
            "retrieve_relevant_glossary_entries() returned no rows for "
            f"the fixed question: {generate_sql.FIXED_QUESTION!r}",
        )

    def test_returns_a_genuine_topk_subset_not_the_full_glossary(self):
        # Per the brief's explicit precedent: never a hardcoded full-list
        # assertion. The "full glossary" size is queried live from
        # app.kb_chunks (populated by the real embed run above), not
        # hardcoded to ~15/~16.
        self.assertIsNotNone(
            self.total_kb_chunk_count,
            "could not determine the live app.kb_chunks row count",
        )
        self.assertGreater(
            self.total_kb_chunk_count,
            1,
            "app.kb_chunks has only one row -- too few to prove top-k "
            "retrieval is a genuine subset",
        )
        self.assertLess(
            len(self.retrieved),
            self.total_kb_chunk_count,
            f"retrieve_relevant_glossary_entries() returned "
            f"{len(self.retrieved)} entries out of "
            f"{self.total_kb_chunk_count} total kb_chunks rows -- "
            "expected a genuine top-k subset, not the full glossary",
        )

    def test_topk_includes_a_semantically_relevant_kpi_for_the_fixed_question(self):
        # FIXED_QUESTION asks about "top 5 product categories by number
        # of orders" -- the glossary's "Top Product Category" KPI is the
        # directly relevant entry. Checked loosely across every string
        # field of every returned row (rather than assuming a specific
        # tuple position for 'source' vs 'content'), since the brief
        # does not pin down the exact return shape beyond "analogous to
        # retrieve_relevant_tables()".
        all_text = " ".join(
            str(field)
            for row in self.retrieved
            for field in row
            if isinstance(field, str)
        ).lower()
        self.assertIn(
            "categor",
            all_text,
            "retrieve_relevant_glossary_entries() did not surface any "
            "category-related glossary entry (e.g. 'Top Product "
            f"Category') for the fixed question. Retrieved rows: "
            f"{self.retrieved!r}",
        )


if __name__ == "__main__":
    unittest.main()
