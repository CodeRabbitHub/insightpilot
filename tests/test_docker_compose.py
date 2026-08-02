"""
Structural checks on docker-compose.yml against the brief's Outputs line:
"docker-compose.yml -- db service only (postgres:16 + pgvector image,
volume, env-driven credentials)".

Plain text/regex checks rather than a YAML parse, to avoid adding a new
dependency (PyYAML) for a one-slice test file. If the file is missing,
these fail honestly (FileNotFoundError) rather than skipping.
"""
import re
import unittest

from _pg_helpers import REPO_ROOT

COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"


class DockerComposeTests(unittest.TestCase):
    def test_compose_file_exists(self):
        self.assertTrue(
            COMPOSE_FILE.exists(), "docker-compose.yml is missing from repo root"
        )

    def test_defines_a_db_service(self):
        text = COMPOSE_FILE.read_text(encoding="utf-8")
        self.assertRegex(
            text,
            re.compile(r"^\s*db:\s*$", re.MULTILINE),
            "docker-compose.yml has no top-level 'db' service",
        )

    def test_db_image_is_postgres_16_with_pgvector(self):
        text = COMPOSE_FILE.read_text(encoding="utf-8")
        image_lines = [line for line in text.splitlines() if "image:" in line]
        self.assertTrue(
            any(
                "16" in line and re.search(r"pgvector", line, re.IGNORECASE)
                for line in image_lines
            ),
            f"no image: line references both postgres 16 and pgvector; found {image_lines}",
        )

    def test_credentials_are_env_driven_not_hardcoded(self):
        text = COMPOSE_FILE.read_text(encoding="utf-8")
        has_env_file = "env_file" in text
        has_var_substitution = bool(re.search(r"\$\{POSTGRES_", text))
        self.assertTrue(
            has_env_file or has_var_substitution,
            "docker-compose.yml does not appear to source Postgres "
            "credentials from the environment (no env_file: or "
            "${POSTGRES_*} substitution found)",
        )

    def test_declares_a_persistent_volume(self):
        text = COMPOSE_FILE.read_text(encoding="utf-8")
        self.assertIn(
            "/var/lib/postgresql/data",
            text,
            "no volume mounted at the Postgres data directory",
        )

    def test_no_api_or_web_service_yet(self):
        # Out-of-scope per the brief: "no app schema, no FastAPI ... in
        # this slice" and Outputs says "db service only".
        text = COMPOSE_FILE.read_text(encoding="utf-8")
        for service in ("api", "web"):
            self.assertNotRegex(
                text,
                re.compile(rf"^\s*{service}:\s*$", re.MULTILINE),
                f"docker-compose.yml defines a '{service}' service, "
                "out of scope for this slice",
            )


if __name__ == "__main__":
    unittest.main()
