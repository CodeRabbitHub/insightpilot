"""
Shared helper for the analyze_answer pipeline step's CLI done-check test
(test_verify_analyze_answer_script.py). Mirrors _answer_helpers.py's
subprocess-invocation pattern for this brief's exact done-check command
(`python -m app.pipeline.verify_analyze_answer`,
plans/briefs/2026-08-05-analyze-answer.md).

verify_analyze_answer chains a real get_answer() call (generate_sql() +
validate_sql() + execute_sql() -- itself two Voyage embed calls plus one
Anthropic call) with a second, real Anthropic call via analyze_answer().
Callers should avoid invoking run_verify_analyze_answer() more often than
the test coverage actually requires.
"""
import subprocess
import sys

from _pg_helpers import REPO_ROOT

# Two chained real API call groups: get_answer()'s own chain (padded to
# 120s in _answer_helpers.py's VERIFY_ANSWER_TIMEOUT_SECONDS) plus a
# second, real Anthropic call via analyze_answer() -- padded with extra
# headroom for the second call rather than assumed to be free.
VERIFY_ANALYZE_ANSWER_TIMEOUT_SECONDS = 180


def run_verify_analyze_answer():
    return subprocess.run(
        [sys.executable, "-m", "app.pipeline.verify_analyze_answer"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=VERIFY_ANALYZE_ANSWER_TIMEOUT_SECONDS,
    )
