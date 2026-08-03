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

# answer() -> generate_sql() now makes two Voyage embed calls per
# invocation (schema + glossary retrieval, since the glossary-retrieval
# slice: plans/briefs/2026-08-03-glossary-retrieval.md), each subject to
# embed_text()'s up-to-6-attempt/20s-backoff retry under Voyage's 3 RPM
# free-tier cap (100s worst case, per call) -- 120s was already tight
# before either change and proved too tight after, so this mirrors
# stop_verify.py's own real-runtime-driven timeout bump from the prior
# slice.
VERIFY_ANSWER_TIMEOUT_SECONDS = 450


def run_verify_answer():
    return subprocess.run(
        [sys.executable, "-m", "app.pipeline.verify_answer"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=VERIFY_ANSWER_TIMEOUT_SECONDS,
    )
