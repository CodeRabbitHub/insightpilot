"""
Shared helpers for the llm-table-descriptions tests (test_describe_cli.py,
test_verify_describe_script.py).

Mirrors _catalog_helpers.py's structure: CLI invocation matching the
brief's exact commands (`python -m app.catalog.describe`, `python -m
app.catalog.verify_describe`). Unlike sync.py, describe.py makes real,
billed calls to the Anthropic API for any catalog_tables row whose
description is still NULL -- callers should avoid invoking run_describe()
more often than necessary once all 9 rows are described, since a
non-NULL description must make describe.py skip that table (never
re-call the LLM for it) per the brief's "run once, cached" requirement.
"""
import subprocess
import sys
import time

from _pg_helpers import REPO_ROOT

# Generous: the first-ever run against a freshly-synced (all-NULL)
# catalog makes up to 9 real, sequential Claude API calls (each with up
# to one retry). Re-runs, once every row is already described, should be
# dominated by DB round-trips and complete far faster than this ceiling.
DESCRIBE_TIMEOUT_SECONDS = 600
VERIFY_DESCRIBE_TIMEOUT_SECONDS = 120


def run_describe():
    return subprocess.run(
        [sys.executable, "-m", "app.catalog.describe"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=DESCRIBE_TIMEOUT_SECONDS,
    )


def timed_run_describe():
    """Like run_describe(), but also returns wall-clock seconds elapsed.

    Used as a black-box (no network mocking) signal for whether a run
    made real LLM calls versus skipped every already-described table:
    9 real sequential Claude calls take far longer than 9 DB skip-checks.
    """
    start = time.monotonic()
    result = run_describe()
    elapsed = time.monotonic() - start
    return result, elapsed


def run_verify_describe():
    return subprocess.run(
        [sys.executable, "-m", "app.catalog.verify_describe"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=VERIFY_DESCRIBE_TIMEOUT_SECONDS,
    )
