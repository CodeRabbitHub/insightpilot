import sqlglot
from sqlglot import exp
from sqlglot.errors import OptimizeError, ParseError
from sqlglot.optimizer.qualify import qualify

DIALECT = "postgres"


class SqlValidationError(Exception):
    """Raised when generated SQL fails the sqlglot validation gate."""


def fetch_catalog_schema(cur):
    """{table_name: {column_name: data_type}}, live from
    app.catalog_tables/app.catalog_columns -- never hardcoded."""
    cur.execute("SELECT id, table_name FROM app.catalog_tables")
    id_to_name = dict(cur.fetchall())
    schema = {table_name: {} for table_name in id_to_name.values()}

    cur.execute("SELECT table_id, column_name, data_type FROM app.catalog_columns")
    for table_id, column_name, data_type in cur.fetchall():
        schema[id_to_name[table_id]][column_name] = data_type

    return schema


def parse_single_select(sql):
    try:
        statements = [s for s in sqlglot.parse(sql, read=DIALECT) if s is not None]
    except ParseError as exc:
        raise SqlValidationError(f"failed to parse SQL: {exc}") from exc

    if len(statements) != 1:
        raise SqlValidationError(
            f"expected exactly one SQL statement, found {len(statements)}"
        )

    statement = statements[0]
    if not isinstance(statement, exp.Select):
        raise SqlValidationError(
            f"expected a SELECT statement, found {type(statement).__name__}"
        )
    return statement


def check_table_references(statement, valid_tables):
    # A CTE's own name is not a catalog table -- e.g. `WITH recent AS
    # (...) SELECT * FROM recent` must not flag `recent` as unknown.
    # Postgres folds unquoted identifiers to lowercase, so both the CTE
    # names and valid_tables are compared case-insensitively, matching the
    # qualifier check below rather than only normalizing that one field.
    cte_names = {cte.alias_or_name.lower() for cte in statement.find_all(exp.CTE)}
    valid_tables_lower = {name.lower() for name in valid_tables}

    unknown = set()
    for table in statement.find_all(exp.Table):
        name = table.name
        # Combine both qualifier parts sqlglot exposes (catalog.schema)
        # instead of checking .db alone -- some parse shapes (a bare
        # "catalog..table" double-dot form) leave .db empty while .catalog
        # carries the qualifying text, and checking only one field would
        # let that shape smuggle a reference past the schema check below.
        qualifier = ".".join(part for part in (table.catalog, table.db) if part)

        # A CTE is only ever addressed unqualified -- any qualifier present
        # can never actually be the CTE, so this exemption must not apply
        # once one is, or a same-named CTE would mask a real cross-schema/
        # catalog leak.
        if not qualifier and name.lower() in cte_names:
            continue
        # Any qualifier other than exactly "olist" (e.g. pg_catalog, or a
        # 3-part catalog.schema.table reference) must be rejected even when
        # the table's basename happens to also be a real olist table.
        if qualifier and qualifier.lower() != "olist":
            unknown.add(f"{qualifier}.{name}")
        elif name.lower() not in valid_tables_lower:
            # A table-valued function call (e.g. generate_series(1, 10))
            # also parses as exp.Table but with an empty .name -- fall back
            # to the node's own SQL so the message still names the actual
            # problem instead of reading as a bare "olist.".
            unknown.add(f"{qualifier or 'olist'}.{name}" if name else table.sql())

    if unknown:
        raise SqlValidationError(
            f"unknown table(s) referenced: {', '.join(sorted(unknown))}"
        )


def check_column_references(statement, schema):
    try:
        qualify(
            statement,
            schema={"olist": schema},
            dialect=DIALECT,
            validate_qualify_columns=True,
        )
    except OptimizeError as exc:
        raise SqlValidationError(f"unknown column referenced: {exc}") from exc


def validate_sql(sql, cur):
    """Raise SqlValidationError naming the problem if `sql` is not exactly
    one SELECT statement referencing only real olist.* tables/columns.
    Returns None on success."""
    schema = fetch_catalog_schema(cur)
    statement = parse_single_select(sql)
    check_table_references(statement, set(schema))
    check_column_references(statement, schema)
