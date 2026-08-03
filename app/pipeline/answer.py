import asyncio

from dotenv import load_dotenv

from app.catalog.sync import connect
from app.pipeline.execute_sql import execute_sql
from app.pipeline.generate_sql import FIXED_QUESTION, generate_sql
from app.pipeline.repair_sql import repair_sql
from app.pipeline.validate_sql import validate_sql

load_dotenv()


async def _validate_and_execute(sql):
    """Validate `sql` against the owner-role connection (schema/catalog
    lookups), then execute it separately through execute_sql()'s own
    read-only connection -- the two never share a connection or role.
    Returns (sql, rows)."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            validate_sql(sql, cur)
    finally:
        conn.close()

    rows = await execute_sql(sql)
    return sql, rows


async def _retry_once(attempt, recover):
    """Run `attempt()`; on any exception, run `recover(exc)` once and
    return its result. A failure from `recover` itself propagates
    unmodified -- this is PRD F2's one-shot repair loop, max 2 attempts
    total, in its pure control-flow shape, with no I/O of its own. Kept
    separate from repair_sql()/execute_sql()'s real network/DB calls so
    the propagation behavior is testable with plain functions, without
    mocking either."""
    try:
        return await attempt()
    except Exception as exc:
        return await recover(exc)


async def _answer_with_repair(question, sql):
    """Validate+execute `sql`; on any failure, repair once via
    repair_sql() and retry -- PRD F2's one-shot repair loop, max 2
    attempts total. A second failure propagates unmodified."""

    async def attempt():
        return await _validate_and_execute(sql)

    async def recover(exc):
        repaired_sql = repair_sql(question, sql, str(exc))
        return await _validate_and_execute(repaired_sql)

    return await _retry_once(attempt, recover)


async def get_answer(question=FIXED_QUESTION):
    """Chain generate_sql() -> validate_sql() -> execute_sql() for the
    given question (default FIXED_QUESTION), repairing once via
    repair_sql() if the first attempt fails validation or execution.
    Returns (sql, rows)."""
    sql = generate_sql(question)
    return await _answer_with_repair(question, sql)


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
