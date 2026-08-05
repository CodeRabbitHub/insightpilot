import asyncio
import sys

from dotenv import load_dotenv

from app.pipeline.analyze_answer import analyze_answer
from app.pipeline.answer import get_answer
from app.pipeline.generate_sql import FIXED_QUESTION
from app.pipeline.validate_sql import SqlValidationError

load_dotenv()


async def run():
    try:
        sql, rows = await get_answer(FIXED_QUESTION)
        result = analyze_answer(FIXED_QUESTION, sql, rows)
    except (SqlValidationError, RuntimeError) as exc:
        print("verify_analyze_answer: FAILED")
        print(f"  - {exc}")
        return 1

    failures = []
    if not result.summary.strip():
        failures.append("summary is blank")
    if not result.explanation.strip():
        failures.append("explanation is blank")
    if not isinstance(result.chart_spec, dict):
        failures.append("chart_spec is not a dict")
    if not result.follow_ups:
        failures.append("follow_ups is empty")

    print(f"Summary:\n{result.summary}\n")
    print(f"Explanation:\n{result.explanation}\n")
    print(f"Chart spec:\n{result.chart_spec}\n")
    print(f"Follow-ups:\n{result.follow_ups}\n")

    if failures:
        print("verify_analyze_answer: FAILED")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("verify_analyze_answer: PASSED")
    return 0


def main():
    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
