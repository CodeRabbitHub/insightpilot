"""
Pure, no-network, no-DB tests for the glossary-retrieval brief's glossary
chunking (plans/briefs/2026-08-03-glossary-retrieval.md): `glossary.md` at
the repo root holds ~15 KPI definitions per PRD.md F5, each a `## <KPI
name>` section, and `app/glossary/embed.py`'s `parse_glossary_entries()`
chunks that file's text into one retrieval chunk per heading.

GlossaryMarkdownFileTests checks only the checked-in glossary.md content
itself (no import from app.glossary), so a missing/broken
app/glossary/embed.py module reports as a separate, later failure rather
than masking a genuine content problem.

GlossaryParsingTests then imports `parse_glossary_entries` from the new
`app.glossary.embed` module (not yet implemented) and checks its output
against the file's real, live content -- never a hardcoded entry count,
per the brief's own precedent ("never a hardcoded full-list check").

Assumed contract for parse_glossary_entries(text), since the brief names
the function but not its exact signature/return shape: it takes the raw
glossary.md text as a single string argument and returns a list of
(source, content) 2-tuples, one per `## ` heading -- analogous to how
`app.catalog.describe.fetch_tables` returns one row per catalog entity.
If the real implementation instead reads the file itself or returns a
different shape, these tests should be read as a proposal, not a
brief-mandated requirement, and adjusted accordingly.

Will fail honestly until app/glossary/embed.py (and parse_glossary_entries)
exist.
"""
import unittest

from _pg_helpers import REPO_ROOT

GLOSSARY_FILE = REPO_ROOT / "glossary.md"


def _heading_lines(text):
    return [line for line in text.splitlines() if line.startswith("## ")]


class GlossaryMarkdownFileTests(unittest.TestCase):
    """Checks glossary.md's own real content -- no app.glossary import."""

    @classmethod
    def setUpClass(cls):
        cls.text = GLOSSARY_FILE.read_text(encoding="utf-8")

    def test_glossary_file_exists_and_is_non_trivial(self):
        self.assertTrue(GLOSSARY_FILE.exists(), "glossary.md is missing at the repo root")
        self.assertGreater(
            len(self.text.strip()),
            500,
            "glossary.md is too short to hold ~15 real KPI definitions",
        )

    def test_glossary_file_has_at_least_ten_kpi_headings(self):
        # Brief says "~15" KPIs -- bounded, not hardcoded, per the
        # instructions to avoid asserting an exact count.
        headings = _heading_lines(self.text)
        self.assertGreaterEqual(
            len(headings),
            10,
            f"glossary.md has only {len(headings)} '## ' headings, expected "
            "~15 KPI definitions per PRD.md F5",
        )

    def test_glossary_headings_are_unique(self):
        headings = _heading_lines(self.text)
        self.assertEqual(
            len(headings),
            len(set(headings)),
            f"glossary.md has duplicate KPI headings: {headings}",
        )

    def test_glossary_entries_reference_real_olist_columns(self):
        # Constraint: "each with an exact formula referencing real olist
        # columns -- verified against the live schema, not invented."
        # A cheap proxy check: schema-qualified references must actually
        # appear (not just KPI prose with no real column names).
        self.assertIn(
            "olist.",
            self.text,
            "glossary.md contains no olist.<table>.<column> style "
            "references -- formulas must reference real schema objects",
        )

    def test_revenue_entry_references_order_items_price(self):
        # A concrete, non-invented formula check for one specific KPI
        # this brief explicitly names (PRD.md F5's Revenue KPI).
        self.assertIn(
            "order_items.price",
            self.text,
            "glossary.md's Revenue-style entry does not reference the "
            "real olist.order_items.price column",
        )


class GlossaryParsingTests(unittest.TestCase):
    """Exercises app.glossary.embed.parse_glossary_entries against the
    real, live glossary.md content."""

    @classmethod
    def setUpClass(cls):
        cls.text = GLOSSARY_FILE.read_text(encoding="utf-8")

    def _parse(self):
        from app.glossary.embed import parse_glossary_entries

        return parse_glossary_entries(self.text)

    def test_parse_glossary_entries_returns_more_than_one_chunk(self):
        entries = self._parse()
        self.assertGreater(
            len(entries),
            1,
            "parse_glossary_entries() must split glossary.md into "
            "multiple retrieval chunks, not treat it as one blob",
        )

    def test_parse_glossary_entries_matches_the_live_heading_count(self):
        # Never a hardcoded number: derived live from the same file the
        # parser is fed, per the schema-retrieval slice's own precedent
        # against hardcoded full-list/full-count assertions.
        entries = self._parse()
        expected_count = len(_heading_lines(self.text))
        self.assertEqual(
            len(entries),
            expected_count,
            f"parse_glossary_entries() returned {len(entries)} entries, "
            f"but glossary.md has {expected_count} '## ' headings -- "
            "every heading should become exactly one chunk",
        )

    def test_each_entry_has_a_nonempty_source_and_content(self):
        entries = self._parse()
        for entry in entries:
            source, content = entry[0], entry[1]
            with self.subTest(source=source):
                self.assertTrue(
                    str(source).strip(), "an entry has a blank/empty source"
                )
                self.assertTrue(
                    str(content).strip(),
                    f"entry {source!r} has blank/empty content",
                )

    def test_entry_sources_are_unique(self):
        entries = self._parse()
        sources = [entry[0] for entry in entries]
        self.assertEqual(
            len(sources),
            len(set(sources)),
            f"parse_glossary_entries() produced duplicate sources: {sources}",
        )

    def test_an_entry_exists_for_the_revenue_kpi_with_its_real_formula(self):
        entries = self._parse()
        revenue_entries = [
            (source, content)
            for source, content in ((e[0], e[1]) for e in entries)
            if "revenue" in str(source).lower()
        ]
        self.assertTrue(
            revenue_entries,
            "no parsed entry's source references 'revenue' -- expected a "
            f"Revenue KPI entry per PRD.md F5, got sources: "
            f"{[e[0] for e in entries]}",
        )
        self.assertIn(
            "order_items.price",
            revenue_entries[0][1],
            "the parsed Revenue entry's content lost its real "
            "olist.order_items.price formula reference",
        )

    def test_an_entry_exists_for_the_top_product_category_kpi(self):
        # Cross-checked later by test_glossary_retrieval.py's semantic
        # top-k test for the fixed question (about product categories).
        entries = self._parse()
        matches = [
            (source, content)
            for source, content in ((e[0], e[1]) for e in entries)
            if "categor" in str(source).lower()
        ]
        self.assertTrue(
            matches,
            "no parsed entry's source references a product-category KPI "
            f"-- expected a Top Product Category entry, got sources: "
            f"{[e[0] for e in entries]}",
        )

    def test_parsing_is_deterministic(self):
        first = self._parse()
        second = self._parse()
        self.assertEqual(
            first,
            second,
            "parse_glossary_entries() returned different results across "
            "two calls on the same input text",
        )


if __name__ == "__main__":
    unittest.main()
