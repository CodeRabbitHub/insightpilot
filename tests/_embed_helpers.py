"""
Shared helpers for the pgvector-schema-retrieval tests (test_catalog_embed.py,
test_verify_embed_script.py).

Mirrors _describe_helpers.py's structure: CLI invocation matching the
brief's exact commands (`python -m app.catalog.embed`, `python -m
app.catalog.verify_embed`). Like describe.py, embed.py makes real, billed
calls to the Voyage AI API for any catalog_tables row not yet present in
app.catalog_embeddings -- callers should avoid invoking run_embed() more
often than necessary once all 9 rows are embedded, since an
already-embedded table_id must make embed.py skip that table (never
re-call Voyage for it) per the brief's "idempotent, safe to re-run" shape.

Voyage's free tier on this project's account has a 3 RPM rate limit, so
tests must reuse a single shared run_embed() call per test class rather
than invoking it once per test.
"""
import subprocess
import sys
import time

from _pg_helpers import REPO_ROOT

# Generous: a first-ever run against a freshly-synced-and-described (but
# not-yet-embedded) catalog makes up to 9 real, sequential Voyage API
# calls. Re-runs, once all 9 rows are already embedded, should be
# dominated by DB round-trips and complete far faster than this ceiling.
EMBED_TIMEOUT_SECONDS = 600
VERIFY_EMBED_TIMEOUT_SECONDS = 120


def run_embed():
    return subprocess.run(
        [sys.executable, "-m", "app.catalog.embed"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=EMBED_TIMEOUT_SECONDS,
    )


def timed_run_embed():
    """Like run_embed(), but also returns wall-clock seconds elapsed.

    Used as a black-box (no network mocking) signal for whether a run
    made real Voyage API calls versus skipped every already-embedded
    table: 9 real sequential embed calls take far longer than 9 DB
    skip-checks.
    """
    start = time.monotonic()
    result = run_embed()
    elapsed = time.monotonic() - start
    return result, elapsed


def run_verify_embed():
    return subprocess.run(
        [sys.executable, "-m", "app.catalog.verify_embed"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=VERIFY_EMBED_TIMEOUT_SECONDS,
    )
