"""
Checks on .env.example against the brief's Outputs line: ".env.example --
all required env vars with placeholder values" and the Constraints line
"secrets via .env, .env.example committed and kept current".

Extended by plans/briefs/2026-08-02-llm-table-descriptions.md: a new
`ANTHROPIC_API_KEY` var (plus an env-configurable model-name var) must be
added alongside the existing connection vars.
"""
import re
import unittest

from _pg_helpers import REPO_ROOT

ENV_EXAMPLE_FILE = REPO_ROOT / ".env.example"

REQUIRED_VARS = (
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "OLIST_RO_USER",
    "OLIST_RO_PASSWORD",
    "ANTHROPIC_API_KEY",
)


class EnvExampleTests(unittest.TestCase):
    def test_env_example_exists(self):
        self.assertTrue(
            ENV_EXAMPLE_FILE.exists(), ".env.example is missing from repo root"
        )

    def test_contains_all_required_connection_vars(self):
        text = ENV_EXAMPLE_FILE.read_text(encoding="utf-8")
        missing = [
            var
            for var in REQUIRED_VARS
            if not re.search(rf"^{var}=.+$", text, re.MULTILINE)
        ]
        self.assertEqual(
            missing,
            [],
            f".env.example is missing (or has empty) values for: {missing}",
        )

    def test_contains_an_env_configurable_anthropic_model_name_var(self):
        # The brief requires the model name to be env-configurable (not
        # hardcoded), without mandating an exact var name, so this matches
        # any ANTHROPIC_*MODEL* assignment rather than one hardcoded name.
        text = ENV_EXAMPLE_FILE.read_text(encoding="utf-8")
        self.assertRegex(
            text,
            re.compile(r"^ANTHROPIC[A-Z_]*MODEL[A-Z_]*=.+$", re.MULTILINE),
            ".env.example has no ANTHROPIC_*MODEL* var for an "
            "env-configurable model name",
        )


if __name__ == "__main__":
    unittest.main()
