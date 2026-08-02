import sys

from dotenv import load_dotenv

from app.catalog.sync import connect
from app.pipeline.generate_sql import generate_sql
from app.pipeline.validate_sql import SqlValidationError, validate_sql

load_dotenv()


def main():
    sql = generate_sql()
    print(f"Generated SQL:\n{sql}\n")

    failures = []

    conn = connect()
    try:
        with conn.cursor() as cur:
            validate_sql(sql, cur)
    except SqlValidationError as exc:
        failures.append(str(exc))
    finally:
        conn.close()

    if failures:
        print("verify_generate_sql: FAILED")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)

    print("verify_generate_sql: PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
