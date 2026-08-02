import asyncpg
from sqlglot import exp

from app.catalog.sync import require_env
from app.pipeline.validate_sql import DIALECT, SqlValidationError, parse_single_select

DEFAULT_LIMIT_CAP = 1000
STATEMENT_TIMEOUT = "10s"


def cap_limit(sql, cap=DEFAULT_LIMIT_CAP):
    """Return `sql` (a single SELECT statement) rendered with its LIMIT
    tightened to at most `cap` -- adding one if none exists, never
    loosening an existing tighter LIMIT. Modifies the sqlglot-parsed
    statement rather than the raw SQL text."""
    statement = parse_single_select(sql)
    existing = statement.args.get("limit")
    if existing is None:
        statement.set("limit", exp.Limit(expression=exp.Literal.number(cap)))
    elif not isinstance(existing.expression, exp.Literal) or existing.expression.is_string:
        # e.g. `LIMIT (SELECT ...)` -- not a plain integer we can compare
        # against the cap. Fail closed with a message naming the problem,
        # rather than let int() raise an uninformative TypeError deep in
        # this defense-in-depth layer.
        raise SqlValidationError(
            f"unsupported LIMIT expression, expected a plain integer "
            f"literal: {existing.sql(dialect=DIALECT)}"
        )
    elif int(existing.expression.this) > cap:
        existing.set("expression", exp.Literal.number(cap))
    return statement.sql(dialect=DIALECT)


async def execute_sql(sql):
    """Run `sql` (a single, already-validated SELECT) for real, through a
    read-only asyncpg connection authenticated as OLIST_RO_USER -- never
    the owner role. Injects a LIMIT cap and a query-scoped
    statement_timeout (ARCHITECT.md's defense-in-depth layer 3) before
    executing. Returns the result rows as a list of dicts."""
    capped_sql = cap_limit(sql)

    conn = await asyncpg.connect(
        host=require_env("POSTGRES_HOST"),
        port=int(require_env("POSTGRES_PORT")),
        database=require_env("POSTGRES_DB"),
        user=require_env("OLIST_RO_USER"),
        password=require_env("OLIST_RO_PASSWORD"),
    )
    try:
        async with conn.transaction():
            await conn.execute(f"SET LOCAL statement_timeout = '{STATEMENT_TIMEOUT}'")
            records = await conn.fetch(capped_sql)
        return [dict(record) for record in records]
    finally:
        await conn.close()
