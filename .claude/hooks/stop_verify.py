"""Stop hook: the build loop. When the agent claims it is done, run the
test suite. Failures bounce the agent back to work — capped at 3 attempts,
then the circuit breaker fires and demands a re-plan instead of a 4th try.

The Stop event fires on every turn, not just ones that touch code —
reviewing a plan, writing a brief, writing a log, plain conversation. To
avoid re-running the full (real API calls, ~200-250s) suite on every one
of those, a run is skipped when the content of every test-relevant path
(WATCHED_PATHS below) matches the signature recorded the last time the
suite was seen to PASS for that exact content. Deliberately keyed to
"last known PASSING state", not "last run" or "last content seen": if
the signature only meant "unchanged since any last run", an unchanged
turn during an active failing retry loop would skip straight to
`return 0` and let the agent stop while tests are still red. Recording
the signature only on a pass means a failing state never matches, so an
unchanged turn during a retry loop still re-runs and still enforces the
attempt count / circuit breaker exactly as before; only a turn where the
watched content matches an already-*verified* state gets skipped.

Exit 2 = the agent is not allowed to stop; stderr tells it why.
State files (gitignored): .claude/.stop_attempts, .claude/.replan_needed,
.claude/.last_verified_signature
"""
import hashlib
import json
import pathlib
import subprocess
import sys

# sys.executable is whatever interpreter launched this hook, which may be
# an isolated harness venv with none of the project's dependencies
# installed -- prefer the project's own .venv when one exists.
_VENV_PYTHON = pathlib.Path(".venv/Scripts/python.exe")
if not _VENV_PYTHON.exists():
    _VENV_PYTHON = pathlib.Path(".venv/bin/python")
PYTHON = str(_VENV_PYTHON) if _VENV_PYTHON.exists() else sys.executable

TEST_CMD = [PYTHON, "-m", "unittest", "discover", "tests"]
MAX_ATTEMPTS = 3

ATTEMPTS = pathlib.Path(".claude/.stop_attempts")
REPLAN = pathlib.Path(".claude/.replan_needed")
LAST_VERIFIED = pathlib.Path(".claude/.last_verified_signature")

# Paths whose content can change what the suite does or how it behaves.
# plans/, HANDOFF.md, artifacts/, and other brief/log/handoff bookkeeping
# are deliberately excluded -- editing those can't change a test outcome.
WATCHED_PATHS = [
    pathlib.Path("app"),
    pathlib.Path("tests"),
    pathlib.Path("prompts"),
    pathlib.Path("alembic"),
    pathlib.Path("alembic.ini"),
    pathlib.Path("requirements.txt"),
]


def _watched_files():
    for watched in WATCHED_PATHS:
        if watched.is_file():
            yield watched
        elif watched.is_dir():
            for path in watched.rglob("*"):
                if path.is_file() and "__pycache__" not in path.parts:
                    yield path


def _watched_signature() -> str:
    """A single hash of every watched file's path and content. Reused,
    not diffed against git, so it works the same whether a change is
    committed, staged, or just sitting in the working tree."""
    hasher = hashlib.sha256()
    for path in sorted(_watched_files(), key=lambda p: p.as_posix()):
        hasher.update(path.as_posix().encode())
        try:
            hasher.update(path.read_bytes())
        except OSError:
            continue
    return hasher.hexdigest()


def main() -> int:
    try:
        json.load(sys.stdin)
    except json.JSONDecodeError:
        pass

    if not pathlib.Path("tests").is_dir():
        return 0

    signature = _watched_signature()
    if LAST_VERIFIED.exists() and LAST_VERIFIED.read_text().strip() == signature:
        # Nothing that can affect a test outcome changed since the last
        # run that actually passed with this exact content -- skip the
        # real-API, ~200-250s suite for a turn that couldn't have broken
        # it (a plan, a brief, a log, conversation).
        return 0

    try:
        # 1200s: the wire-analyze-answer slice (2026-08-05) made get_answer()
        # unconditionally run one more real Anthropic call per question,
        # pushing the full suite's real solo runtime from ~200-250s to
        # ~570-840s -- past the previous 600s timeout, which twice caused a
        # hard kill of this subprocess mid-run in the same session. A
        # shorter timeout doesn't just fail fast -- subprocess.run() kills
        # the child on timeout, which can land mid-way through one of the
        # integration tests that mutates a shared DB row and restores it in
        # a `finally` (e.g. test_catalog_sync.py's preserve-description
        # test): a hard kill skips that `finally`, permanently corrupting
        # the row for every later test run until someone notices and
        # repairs it by hand. 1200s keeps real margin over the new measured
        # runtime while still catching a genuine hang in ~20 minutes.
        result = subprocess.run(
            TEST_CMD, capture_output=True, text=True, timeout=1200
        )
    except Exception:
        return 0

    if result.returncode == 0:
        ATTEMPTS.unlink(missing_ok=True)
        REPLAN.unlink(missing_ok=True)
        LAST_VERIFIED.write_text(signature)
        return 0

    # Breaker already fired: let the session stop so the human can re-plan.
    if REPLAN.exists():
        return 0

    attempts = int(ATTEMPTS.read_text()) + 1 if ATTEMPTS.exists() else 1
    tail = "\n".join((result.stderr or result.stdout).splitlines()[-30:])

    if attempts >= MAX_ATTEMPTS:
        ATTEMPTS.unlink(missing_ok=True)
        REPLAN.touch()
        print(
            "CIRCUIT BREAKER: tests failed on 3 attempts. Do NOT attempt "
            "another fix and do NOT weaken any test. Summarize what each "
            "of the three attempts revealed, then ask the user to re-plan "
            "the slice.\n" + tail,
            file=sys.stderr,
        )
        return 2

    ATTEMPTS.write_text(str(attempts))
    print(
        f"Tests failing (attempt {attempts}/{MAX_ATTEMPTS}). Not done - "
        "fix the code, never the test, and try again.\n" + tail,
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
