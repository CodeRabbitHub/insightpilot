"""
Structural checks for the llm-table-descriptions brief's Constraints
(plans/briefs/2026-08-02-llm-table-descriptions.md): the two
pre-approved new dependencies (`anthropic`, `pydantic`) land in
requirements.txt with no other new dependencies added alongside them,
and the LLM prompt lives in a real, versioned file
(`prompts/table_description.md`) rather than an inline string.

Note: the brief's "never an inline string" half of that prompt
constraint (i.e. that app/catalog/describe.py itself loads this file
rather than embedding prompt text) is not checked here -- verifying that
would mean reading describe.py's implementation, which this test-writing
role is deliberately blind to. Only the artifact's existence and
substance are checked as a proxy.
"""
import re
import unittest

from _pg_helpers import REPO_ROOT

REQUIREMENTS_FILE = REPO_ROOT / "requirements.txt"
PROMPT_FILE = REPO_ROOT / "prompts" / "table_description.md"

# The dependency set this repo had before this slice (psycopg2-binary,
# python-dotenv per requirements.txt / HANDOFF.md from the prior slice),
# so passing proves *only* the two pre-approved packages were added, not
# a loose "at least these exist" check.
PRE_EXISTING_PACKAGES = {"psycopg2-binary", "python-dotenv"}
NEWLY_APPROVED_PACKAGES = {"anthropic", "pydantic"}


def _package_names(text):
    names = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name = re.split(r"[=<>~\[]", line, maxsplit=1)[0].strip()
        if name:
            names.add(name.lower())
    return names


class RequirementsTests(unittest.TestCase):
    def test_requirements_gains_anthropic_and_pydantic(self):
        text = REQUIREMENTS_FILE.read_text(encoding="utf-8")
        names = _package_names(text)
        missing = NEWLY_APPROVED_PACKAGES - names
        self.assertEqual(
            missing,
            set(),
            f"requirements.txt is missing pre-approved new dependencies: {missing}",
        )

    def test_requirements_gains_no_other_new_dependencies(self):
        text = REQUIREMENTS_FILE.read_text(encoding="utf-8")
        names = _package_names(text)
        expected = PRE_EXISTING_PACKAGES | NEWLY_APPROVED_PACKAGES
        unexpected = names - expected
        self.assertEqual(
            unexpected,
            set(),
            "requirements.txt gained dependencies beyond the two "
            f"pre-approved for this slice (anthropic, pydantic): {unexpected}",
        )


class TableDescriptionPromptFileTests(unittest.TestCase):
    def test_prompt_file_exists(self):
        self.assertTrue(
            PROMPT_FILE.exists(),
            "prompts/table_description.md is missing -- the brief requires "
            "the LLM prompt to live in a new versioned file, never an "
            "inline string",
        )

    def test_prompt_file_is_a_substantive_template_not_a_stub(self):
        text = PROMPT_FILE.read_text(encoding="utf-8")
        self.assertGreater(
            len(text.strip()),
            200,
            "prompts/table_description.md is too short to be a real "
            "prompt template",
        )

    def test_prompt_instructs_a_json_response(self):
        # The response is Pydantic-validated JSON per the brief's
        # Constraints ("validates the LLM's JSON output"); the prompt
        # feeding that model must therefore ask for JSON.
        text = PROMPT_FILE.read_text(encoding="utf-8")
        self.assertIn(
            "json",
            text.lower(),
            "prompts/table_description.md does not appear to instruct the "
            "model to respond with JSON",
        )

    def test_prompt_references_a_description_field(self):
        text = PROMPT_FILE.read_text(encoding="utf-8")
        self.assertIn(
            "description",
            text.lower(),
            "prompts/table_description.md does not reference a "
            "'description' field for the LLM to produce",
        )


if __name__ == "__main__":
    unittest.main()
