"""
The concurrency-safety brief's done-check
(plans/briefs/2026-08-03-concurrency-safety.md): proves the advisory-lock
fix in test_verify_describe_script.py / test_glossary_verify_embed.py
holds under real concurrent execution, catching the shared-DB-row race
the Stop hook's automatic full-suite run can trigger when it overlaps a
manual run (HANDOFF.md, 2026-08-03).

Launches multiple concurrent subprocess invocations of both racy test
files -- the same `unittest discover -s tests -p <file>` invocation this
project already uses to run one test file standalone -- and asserts every
invocation exits 0.

Run as `python -m tests.verify_concurrency_safety`: this script itself
does no bare sibling import, so it's unaffected by `tests/` having no
`__init__.py` (that only matters for the test files' own bare
`from _pg_helpers import ...`, resolved via `unittest discover`'s sys.path
insertion, which each subprocess triggers independently).
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_PER_FILE = 2
TIMEOUT_SECONDS = 300

RACY_TEST_FILES = [
    "test_verify_describe_script.py",
    "test_glossary_verify_embed.py",
]


def _launch(test_file):
    return subprocess.Popen(
        [
            sys.executable, "-m", "unittest", "discover",
            "-s", "tests", "-p", test_file, "-v",
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def main():
    runs = [
        (test_file, run_index, _launch(test_file))
        for test_file in RACY_TEST_FILES
        for run_index in range(RUNS_PER_FILE)
    ]

    failures = []
    for test_file, run_index, proc in runs:
        try:
            _stdout, stderr = proc.communicate(timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            proc.kill()
            _stdout, stderr = proc.communicate()
            print(f"  [FAIL] {test_file} (run {run_index}): "
                  f"timed out after {TIMEOUT_SECONDS}s, killed")
            failures.append(f"{test_file} (run {run_index}): timed out, killed")
            continue

        ok = proc.returncode == 0
        print(f"  [{'OK' if ok else 'FAIL'}] {test_file} (run {run_index}): "
              f"exit={proc.returncode}")
        if not ok:
            failures.append(f"{test_file} (run {run_index}):\n{stderr[-2000:]}")

    if failures:
        print("\nverify_concurrency_safety: FAILED")
        for failure in failures:
            print(failure)
        sys.exit(1)

    print("\nverify_concurrency_safety: PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
