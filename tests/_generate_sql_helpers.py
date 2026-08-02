"""
Shared helpers for the generate-sql-from-a-fixed-question tests
(test_generate_sql_cli.py, test_verify_generate_sql_script.py).

Mirrors _describe_helpers.py's structure: CLI invocation matching the
brief's exact done-check command (`python -m
app.pipeline.verify_generate_sql`). Unlike describe.py, generate_sql.py
has no "already done, skip" cache -- every call to generate_sql()
(directly, via `python -m app.pipeline.generate_sql`, or via the verify
CLI) makes one real, billed Claude API call (plus up to one retry), so
callers should avoid invoking it more often than the test coverage
actually requires.
"""
import subprocess
import sys

from _pg_helpers import REPO_ROOT

VERIFY_GENERATE_SQL_TIMEOUT_SECONDS = 120


def run_verify_generate_sql():
    return subprocess.run(
        [sys.executable, "-m", "app.pipeline.verify_generate_sql"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=VERIFY_GENERATE_SQL_TIMEOUT_SECONDS,
    )
