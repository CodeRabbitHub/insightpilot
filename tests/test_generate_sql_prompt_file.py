"""
Structural checks for the generate-sql-from-a-fixed-question brief's
Constraints (plans/briefs/2026-08-02-generate-sql.md): the LLM prompt
lives in a new, versioned file (prompts/generate_sql.md), string.Template
style like prompts/table_description.md, and it instructs the model to
return exactly one SELECT statement referencing only olist.* tables.

Note: the brief's "never an inline string" half of that constraint (i.e.
that app/pipeline/generate_sql.py itself loads this file from disk rather
than embedding prompt text inline) is not checked here -- verifying that
would mean reading generate_sql.py's implementation, which this
test-writing role is deliberately blind to. Only the artifact's
existence, substance, and Template-substitutability are checked as a
proxy, matching test_llm_description_setup.py's precedent for
table_description.md.

GenerateSqlPromptFileGlossaryContextTests extends this file for the
glossary-retrieval brief (plans/briefs/2026-08-03-glossary-retrieval.md):
"prompts/generate_sql.md gains a glossary-context placeholder (a real
templated section via string.Template, not a hardcoded string)". Mirrors
GenerateSqlPromptFileTests' own $schema_context/$question
substitutability checks, for the new $glossary_context placeholder.
"""
import unittest
from string import Template

from _pg_helpers import REPO_ROOT

PROMPT_FILE = REPO_ROOT / "prompts" / "generate_sql.md"


class GenerateSqlPromptFileTests(unittest.TestCase):
    def test_prompt_file_exists(self):
        self.assertTrue(
            PROMPT_FILE.exists(),
            "prompts/generate_sql.md is missing -- the brief requires the "
            "LLM prompt to live in a new versioned file, never an inline "
            "string",
        )

    def test_prompt_file_is_a_substantive_template_not_a_stub(self):
        text = PROMPT_FILE.read_text(encoding="utf-8")
        self.assertGreater(
            len(text.strip()),
            200,
            "prompts/generate_sql.md is too short to be a real prompt template",
        )

    def test_prompt_is_substitutable_with_schema_context_and_question(self):
        # Also supplies glossary_context: the glossary-retrieval brief
        # (plans/briefs/2026-08-03-glossary-retrieval.md) added a second
        # required placeholder to this same template, so a real render
        # must fill every placeholder the file now declares.
        text = PROMPT_FILE.read_text(encoding="utf-8")
        rendered = Template(text).substitute(
            schema_context="Table: olist.orders\nDescription: ...\n",
            question="What are the top 5 product categories by number of orders?",
            glossary_context="",
        )
        self.assertIn(
            "Table: olist.orders",
            rendered,
            "the $schema_context placeholder was not substituted",
        )
        self.assertIn(
            "What are the top 5 product categories by number of orders?",
            rendered,
            "the $question placeholder was not substituted",
        )

    def test_prompt_instructs_a_json_response(self):
        text = PROMPT_FILE.read_text(encoding="utf-8")
        self.assertIn(
            "json",
            text.lower(),
            "prompts/generate_sql.md does not appear to instruct the model "
            "to respond with JSON",
        )

    def test_prompt_references_a_sql_response_field(self):
        text = PROMPT_FILE.read_text(encoding="utf-8")
        self.assertIn(
            '"sql"',
            text,
            "prompts/generate_sql.md does not reference the expected "
            '{"sql": ...} response field',
        )

    def test_prompt_instructs_select_only_against_olist_tables(self):
        text = PROMPT_FILE.read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertIn(
            "select",
            lowered,
            "prompts/generate_sql.md does not mention SELECT statements",
        )
        self.assertIn(
            "olist",
            lowered,
            "prompts/generate_sql.md does not reference the olist schema",
        )


class GenerateSqlPromptFileGlossaryContextTests(unittest.TestCase):
    """New for plans/briefs/2026-08-03-glossary-retrieval.md: the prompt
    template gains a real, substitutable $glossary_context section."""

    def test_prompt_file_mentions_glossary(self):
        text = PROMPT_FILE.read_text(encoding="utf-8")
        self.assertIn(
            "glossary",
            text.lower(),
            "prompts/generate_sql.md does not mention a business glossary "
            "-- the brief requires a real glossary-context section, not "
            "just a placeholder with no surrounding instructions",
        )

    def test_prompt_has_a_real_glossary_context_placeholder(self):
        # Checked as a literal $glossary_context token in the source
        # text, distinguishing "a real templated section" from a
        # hardcoded string that merely contains the word "glossary".
        text = PROMPT_FILE.read_text(encoding="utf-8")
        self.assertIn(
            "$glossary_context",
            text,
            "prompts/generate_sql.md has no $glossary_context "
            "string.Template placeholder -- the brief requires a real "
            "templated section, not a hardcoded string",
        )

    def test_prompt_is_substitutable_with_glossary_context_alongside_the_rest(self):
        text = PROMPT_FILE.read_text(encoding="utf-8")
        marker = "GLOSSARY_CONTEXT_SUBSTITUTION_MARKER_12345"
        rendered = Template(text).substitute(
            schema_context="Table: olist.orders\nDescription: ...\n",
            question="What are the top 5 product categories by number of orders?",
            glossary_context=marker,
        )
        self.assertIn(
            marker,
            rendered,
            "the $glossary_context placeholder was not substituted into "
            "the rendered prompt",
        )
        # The existing placeholders must keep working unchanged alongside
        # the new one (no regression in the schema-retrieval slice's own
        # prompt substitutability).
        self.assertIn("Table: olist.orders", rendered)
        self.assertIn(
            "What are the top 5 product categories by number of orders?",
            rendered,
        )


if __name__ == "__main__":
    unittest.main()
