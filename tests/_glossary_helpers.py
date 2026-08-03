"""
Shared helpers for the glossary-retrieval tests (test_glossary_embed.py,
test_glossary_verify_embed.py, test_glossary_retrieval.py).

Mirrors _embed_helpers.py's structure exactly, but for the new
`app/glossary/` package (plans/briefs/2026-08-03-glossary-retrieval.md):
CLI invocation matching the brief's proposed commands (`python -m
app.glossary.embed`, `python -m app.glossary.verify_embed`). Named
distinctly from _embed_helpers.py's run_embed()/run_verify_embed() (rather
than reusing those names) so a test file can import both the catalog and
glossary helpers side by side without a name collision.

Like app/catalog/embed.py, app/glossary/embed.py is expected to make real,
billed calls to the Voyage AI API for any glossary chunk not yet present
in app.kb_chunks -- callers should avoid invoking run_glossary_embed() more
often than necessary once every chunk is embedded, since an
already-embedded chunk (by its stable `source` key) must make embed.py
skip it (never re-call Voyage for it) per the brief's "idempotent, safe to
re-run" shape, mirroring app/catalog/embed.py's own contract.

Voyage's free tier on this project's account has a 3 RPM rate limit, so
tests must reuse a single shared run_glossary_embed() call per test class
rather than invoking it once per test.
"""
import subprocess
import sys
import time

from _pg_helpers import REPO_ROOT

# Generous: a first-ever run against a freshly-written, not-yet-embedded
# glossary.md (~15-20 KPI chunks per the brief) makes up to that many
# real, sequential Voyage API calls. Re-runs, once every chunk is already
# embedded, should be dominated by DB round-trips and complete far faster
# than this ceiling.
GLOSSARY_EMBED_TIMEOUT_SECONDS = 600
GLOSSARY_VERIFY_EMBED_TIMEOUT_SECONDS = 120


def run_glossary_embed():
    return subprocess.run(
        [sys.executable, "-m", "app.glossary.embed"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=GLOSSARY_EMBED_TIMEOUT_SECONDS,
    )


def timed_run_glossary_embed():
    """Like run_glossary_embed(), but also returns wall-clock seconds
    elapsed.

    Used as a black-box (no network mocking) signal for whether a run
    made real Voyage API calls versus skipped every already-embedded
    chunk: real sequential embed calls take far longer than DB
    skip-checks alone.
    """
    start = time.monotonic()
    result = run_glossary_embed()
    elapsed = time.monotonic() - start
    return result, elapsed


def run_glossary_verify_embed():
    return subprocess.run(
        [sys.executable, "-m", "app.glossary.verify_embed"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=GLOSSARY_VERIFY_EMBED_TIMEOUT_SECONDS,
    )
