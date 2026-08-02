import asyncio
import sys

from dotenv import load_dotenv

from app.pipeline.answer import get_answer, print_answer
from app.pipeline.validate_sql import SqlValidationError

load_dotenv()


async def run():
    try:
        sql, rows = await get_answer()
    except SqlValidationError as exc:
        print("verify_answer: FAILED")
        print(f"  - {exc}")
        return 1

    print_answer(sql, rows)

    print("\nverify_answer: PASSED")
    return 0


def main():
    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
