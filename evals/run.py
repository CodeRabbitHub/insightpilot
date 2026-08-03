import asyncio
import sys
from decimal import Decimal
from pathlib import Path

import yaml

from app.pipeline.answer import get_answer

REPO_ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_FILE = REPO_ROOT / "evals" / "questions.yaml"


def load_questions(path):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _normalize(value):
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _check_top_row(rows, expected_values):
    first_row_values = [_normalize(v) for v in rows[0].values()]
    return all(_normalize(v) in first_row_values for v in expected_values)


def _check_scalar(rows, expected_value, tolerance):
    row = rows[0]
    if len(row) != 1:
        return False
    (actual,) = row.values()
    actual = _normalize(actual)
    expected_value = _normalize(expected_value)
    if isinstance(expected_value, (int, float)) and not isinstance(expected_value, bool):
        try:
            return abs(float(actual) - float(expected_value)) <= tolerance
        except (TypeError, ValueError):
            return False
    return actual == expected_value


def check_expected(rows, expected):
    """Grade real result `rows` (the list-of-dict shape get_answer()/
    execute_sql() return) against one question's `expected` assertion.
    Never raises -- an empty or malformed result grades as a plain
    failure, so the runner's per-question loop can report PASS/FAIL for
    every case without wrapping each one in a try/except."""
    if not rows:
        return False
    if "top_row" in expected:
        return _check_top_row(rows, expected["top_row"])
    if "scalar" in expected:
        return _check_scalar(rows, expected["scalar"], expected.get("tolerance", 0))
    return False


def format_summary(num_correct, total):
    return f"{num_correct}/{total} correct"


async def _run_question(case):
    try:
        _sql, rows = await get_answer(case["question"])
    except Exception as exc:
        return False, str(exc)
    return check_expected(rows, case["expected"]), None


async def _run_all(questions):
    results = []
    for case in questions:
        passed, error = await _run_question(case)
        results.append((case["question"], passed, error))
    return results


def main():
    questions = load_questions(QUESTIONS_FILE)
    results = asyncio.run(_run_all(questions))

    num_correct = 0
    for question, passed, error in results:
        marker = "PASS" if passed else "FAIL"
        suffix = f" -- {error}" if error else ""
        print(f"[{marker}] {question}{suffix}")
        if passed:
            num_correct += 1

    print(format_summary(num_correct, len(results)))
    sys.exit(0)


if __name__ == "__main__":
    main()
