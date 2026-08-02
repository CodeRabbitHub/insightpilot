"""
Checks on .env.example against the brief's Outputs line: ".env.example --
all required env vars with placeholder values" and the Constraints line
"secrets via .env, .env.example committed and kept current".
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


if __name__ == "__main__":
    unittest.main()
