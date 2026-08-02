"""Stop hook: the build loop. When the agent claims it is done, run the
test suite. Failures bounce the agent back to work — capped at 3 attempts,
then the circuit breaker fires and demands a re-plan instead of a 4th try.

Exit 2 = the agent is not allowed to stop; stderr tells it why.
State files (gitignored): .claude/.stop_attempts, .claude/.replan_needed
"""
import json
import pathlib
import subprocess
import sys

TEST_CMD = [sys.executable, "-m", "unittest", "discover", "tests"]
MAX_ATTEMPTS = 3

ATTEMPTS = pathlib.Path(".claude/.stop_attempts")
REPLAN = pathlib.Path(".claude/.replan_needed")


def main() -> int:
    try:
        json.load(sys.stdin)
    except json.JSONDecodeError:
        pass

    if not pathlib.Path("tests").is_dir():
        return 0

    try:
        result = subprocess.run(
            TEST_CMD, capture_output=True, text=True, timeout=300
        )
    except Exception:
        return 0

    if result.returncode == 0:
        ATTEMPTS.unlink(missing_ok=True)
        REPLAN.unlink(missing_ok=True)
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
