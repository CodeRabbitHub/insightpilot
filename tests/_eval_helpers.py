"""
Shared helper for the eval-harness-v1 brief's literal done-check
(plans/briefs/2026-08-02-eval-harness-v1.md): `python -m evals.run` exits
0 and prints a real accuracy score for the 5 curated questions.

Mirrors _answer_helpers.py's/_generate_sql_helpers.py's subprocess
-invocation pattern. Unlike describe.py's "already done, skip" cache,
evals/run.py has no such cache -- every invocation makes 5 real,
sequential, billed Claude API calls (one per curated question, each via
generate_sql(), plus up to one retry) and 5 real Voyage embedding calls,
so callers should avoid invoking run_evals() more often than the test
coverage actually requires.
"""
import subprocess
import sys

from _pg_helpers import REPO_ROOT

# Generous: 5 real sequential question round-trips (embed -> generate SQL
# -> validate -> execute), each with up to one LLM retry. Mirrors
# _describe_helpers.py's DESCRIBE_TIMEOUT_SECONDS budget for a comparable
# number of sequential real API calls.
RUN_EVALS_TIMEOUT_SECONDS = 600


def run_evals():
    return subprocess.run(
        [sys.executable, "-m", "evals.run"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=RUN_EVALS_TIMEOUT_SECONDS,
    )
