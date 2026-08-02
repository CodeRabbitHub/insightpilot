"""
Shared helper for the execute-sql slice's CLI done-check test
(test_verify_answer_script.py). Mirrors _generate_sql_helpers.py's
subprocess-invocation pattern for this brief's exact done-check command
(`python -m app.pipeline.verify_answer`,
plans/briefs/2026-08-02-execute-sql.md).

Like generate_sql(), the chained answer() flow has no "already done"
cache -- every invocation makes one real, billed Claude API call (via
generate_sql()) plus a real execute against the OLIST_RO_USER asyncpg
connection, so callers should avoid invoking it more often than the test
coverage actually requires.
"""
import subprocess
import sys

from _pg_helpers import REPO_ROOT

VERIFY_ANSWER_TIMEOUT_SECONDS = 120


def run_verify_answer():
    return subprocess.run(
        [sys.executable, "-m", "app.pipeline.verify_answer"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=VERIFY_ANSWER_TIMEOUT_SECONDS,
    )
