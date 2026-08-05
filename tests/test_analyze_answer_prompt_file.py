"""
Structural checks for the analyze_answer pipeline step's prompt file
(plans/briefs/2026-08-05-analyze-answer.md): `prompts/analyze.md`, a new,
versioned, string.Template-based file (never an inline string) with
placeholders for at minimum a question, the executed SQL, and a capped
row sample, instructing the model to respond with JSON containing
{summary, explanation, chart_spec, follow_ups}.

Mirrors test_generate_sql_prompt_file.py's precedent for
prompts/generate_sql.md: only the artifact's existence, substance, and
Template-substitutability are checked here (never analyze_answer.py's
implementation, which this test-writing role is deliberately blind to
until it exists).

The brief deliberately leaves the exact placeholder names to the
implementation ("at minimum a question, the SQL, and a row sample"), so
this file discovers the template's real declared identifiers via
string.Template.get_identifiers() (Python 3.11+) rather than hardcoding a
guess at their names.

Will fail honestly until prompts/analyze.md exists.
"""
import unittest
from string import Template

from _pg_helpers import REPO_ROOT

PROMPT_FILE = REPO_ROOT / "prompts" / "analyze.md"


class AnalyzeAnswerPromptFileTests(unittest.TestCase):
    def test_prompt_file_exists(self):
        self.assertTrue(
            PROMPT_FILE.exists(),
            "prompts/analyze.md is missing -- the brief requires the LLM "
            "prompt to live in a new versioned file, never an inline "
            "string",
        )

    def test_prompt_file_is_a_substantive_template_not_a_stub(self):
        text = PROMPT_FILE.read_text(encoding="utf-8")
        self.assertGreater(
            len(text.strip()),
            200,
            "prompts/analyze.md is too short to be a real prompt template",
        )

    def test_prompt_declares_at_least_three_placeholders(self):
        # "at minimum a question, the SQL, and a row sample" (brief's
        # Constraints) -- checked as a count of distinct string.Template
        # identifiers, not by guessing their exact names.
        text = PROMPT_FILE.read_text(encoding="utf-8")
        identifiers = Template(text).get_identifiers()
        self.assertGreaterEqual(
            len(set(identifiers)),
            3,
            "prompts/analyze.md must declare at least three distinct "
            "string.Template placeholders (question, sql, row sample), "
            f"found: {identifiers!r}",
        )

    def test_prompt_is_substitutable_with_every_declared_placeholder(self):
        text = PROMPT_FILE.read_text(encoding="utf-8")
        identifiers = Template(text).get_identifiers()
        mapping = {
            identifier: f"SUBSTITUTION_MARKER_{identifier.upper()}_12345"
            for identifier in identifiers
        }
        rendered = Template(text).substitute(mapping)
        for identifier, marker in mapping.items():
            self.assertIn(
                marker,
                rendered,
                f"the ${identifier} placeholder was not substituted into "
                "the rendered prompt",
            )

    def test_prompt_mentions_a_question_concept(self):
        text = PROMPT_FILE.read_text(encoding="utf-8")
        self.assertIn(
            "question",
            text.lower(),
            "prompts/analyze.md does not appear to reference the "
            "plain-English question at all",
        )

    def test_prompt_mentions_a_sql_concept(self):
        text = PROMPT_FILE.read_text(encoding="utf-8")
        self.assertIn(
            "sql",
            text.lower(),
            "prompts/analyze.md does not appear to reference the executed "
            "SQL at all",
        )

    def test_prompt_mentions_a_row_sample_concept(self):
        text = PROMPT_FILE.read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertTrue(
            "row" in lowered or "sample" in lowered or "result" in lowered,
            "prompts/analyze.md does not appear to reference the result "
            "row sample at all",
        )

    def test_prompt_instructs_a_json_response(self):
        text = PROMPT_FILE.read_text(encoding="utf-8")
        self.assertIn(
            "json",
            text.lower(),
            "prompts/analyze.md does not appear to instruct the model to "
            "respond with JSON",
        )

    def test_prompt_references_the_summary_response_field(self):
        text = PROMPT_FILE.read_text(encoding="utf-8")
        self.assertIn(
            '"summary"',
            text,
            'prompts/analyze.md does not reference the expected "summary" '
            "response field",
        )

    def test_prompt_references_the_explanation_response_field(self):
        text = PROMPT_FILE.read_text(encoding="utf-8")
        self.assertIn(
            '"explanation"',
            text,
            'prompts/analyze.md does not reference the expected '
            '"explanation" response field',
        )

    def test_prompt_references_the_chart_spec_response_field(self):
        text = PROMPT_FILE.read_text(encoding="utf-8")
        self.assertIn(
            '"chart_spec"',
            text,
            'prompts/analyze.md does not reference the expected '
            '"chart_spec" response field',
        )

    def test_prompt_references_the_follow_ups_response_field(self):
        text = PROMPT_FILE.read_text(encoding="utf-8")
        self.assertIn(
            '"follow_ups"',
            text,
            'prompts/analyze.md does not reference the expected '
            '"follow_ups" response field',
        )


if __name__ == "__main__":
    unittest.main()
