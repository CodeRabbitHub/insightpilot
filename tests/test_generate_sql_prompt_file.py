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
        text = PROMPT_FILE.read_text(encoding="utf-8")
        rendered = Template(text).substitute(
            schema_context="Table: olist.orders\nDescription: ...\n",
            question="What are the top 5 product categories by number of orders?",
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


if __name__ == "__main__":
    unittest.main()
