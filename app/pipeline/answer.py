import asyncio

from dotenv import load_dotenv

from app.catalog.sync import connect
from app.pipeline.execute_sql import execute_sql
from app.pipeline.generate_sql import generate_sql
from app.pipeline.validate_sql import validate_sql

load_dotenv()


async def get_answer():
    """Chain generate_sql() -> validate_sql() -> execute_sql() for the
    fixed question. Returns (sql, rows). Validation runs against the
    owner-role connection (schema/catalog lookups); execution runs
    separately through execute_sql()'s own read-only connection -- the
    two never share a connection or role."""
    sql = generate_sql()

    conn = connect()
    try:
        with conn.cursor() as cur:
            validate_sql(sql, cur)
    finally:
        conn.close()

    rows = await execute_sql(sql)
    return sql, rows


def print_answer(sql, rows):
    print(f"SQL:\n{sql}\n")
    print("Rows:")
    for row in rows:
        print(row)


def main():
    sql, rows = asyncio.run(get_answer())
    print_answer(sql, rows)


if __name__ == "__main__":
    main()
