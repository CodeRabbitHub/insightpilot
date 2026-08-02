import json
import os

import psycopg2
import psycopg2.sql as sql
from dotenv import load_dotenv

load_dotenv()

SCHEMA_DDL = """
CREATE SCHEMA IF NOT EXISTS app;

CREATE TABLE IF NOT EXISTS app.catalog_tables (
    id SERIAL PRIMARY KEY,
    table_name TEXT NOT NULL,
    description TEXT,
    row_count BIGINT NOT NULL,
    ddl_summary TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app.catalog_columns (
    id SERIAL PRIMARY KEY,
    table_id INTEGER NOT NULL REFERENCES app.catalog_tables(id),
    column_name TEXT NOT NULL,
    data_type TEXT NOT NULL,
    is_pk BOOLEAN NOT NULL,
    is_fk BOOLEAN NOT NULL,
    ref_table TEXT,
    sample_values_json JSONB NOT NULL
);
"""


# require_env/connect duplicate scripts/seed.py's helpers of the same name
# rather than being extracted into a shared module: scripts/ and app/ are
# different trees with different futures (app/'s eventual FastAPI code uses
# asyncpg pools per ARCHITECT.md, not this psycopg2 helper), so a shared
# abstraction would be speculative for what is still only the second
# occurrence.
def require_env(name):
    try:
        return os.environ[name]
    except KeyError:
        raise SystemExit(
            f"Missing required env var {name!r}. Copy .env.example to .env "
            "and fill in real values."
        )


def connect():
    # Always the owner role (POSTGRES_USER) -- sync must never run as
    # OLIST_RO_USER, so unlike seed.py's connect() this takes no
    # user/password override.
    return psycopg2.connect(
        host=require_env("POSTGRES_HOST"),
        port=require_env("POSTGRES_PORT"),
        dbname=require_env("POSTGRES_DB"),
        user=require_env("POSTGRES_USER"),
        password=require_env("POSTGRES_PASSWORD"),
    )


def olist_table_names(cur):
    cur.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'olist' AND table_type = 'BASE TABLE' "
        "ORDER BY table_name"
    )
    return [row[0] for row in cur.fetchall()]


def olist_columns(cur, table_name):
    """(column_name, data_type, is_nullable) triples, ordinal order."""
    cur.execute(
        "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
        "WHERE table_schema = 'olist' AND table_name = %s "
        "ORDER BY ordinal_position",
        (table_name,),
    )
    return cur.fetchall()


def olist_row_count(cur, table_name):
    cur.execute(
        sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
            sql.Identifier("olist"), sql.Identifier(table_name)
        )
    )
    return cur.fetchone()[0]


def primary_key_columns_by_table(cur):
    """{table_name: {column_name, ...}} for every real PK column in olist."""
    cur.execute(
        "SELECT tc.table_name, kcu.column_name "
        "FROM information_schema.table_constraints tc "
        "JOIN information_schema.key_column_usage kcu "
        "  ON tc.constraint_name = kcu.constraint_name "
        "  AND tc.table_schema = kcu.table_schema "
        "WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_schema = 'olist'"
    )
    by_table = {}
    for table_name, column_name in cur.fetchall():
        by_table.setdefault(table_name, set()).add(column_name)
    return by_table


def foreign_keys_by_column(cur):
    """{(table_name, column_name): ref_table} for every real FK column in olist."""
    cur.execute(
        "SELECT tc.table_name, kcu.column_name, ccu.table_name "
        "FROM information_schema.table_constraints tc "
        "JOIN information_schema.key_column_usage kcu "
        "  ON tc.constraint_name = kcu.constraint_name "
        "  AND tc.table_schema = kcu.table_schema "
        "JOIN information_schema.constraint_column_usage ccu "
        "  ON tc.constraint_name = ccu.constraint_name "
        "  AND tc.table_schema = ccu.table_schema "
        "WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'olist'"
    )
    return {(table_name, column_name): ref_table for table_name, column_name, ref_table in cur.fetchall()}


def sample_values(cur, table_name, column_name, limit=5):
    cur.execute(
        sql.SQL(
            "SELECT DISTINCT {col} FROM {schema}.{table} "
            "WHERE {col} IS NOT NULL ORDER BY {col} ASC LIMIT %s"
        ).format(
            col=sql.Identifier(column_name),
            schema=sql.Identifier("olist"),
            table=sql.Identifier(table_name),
        ),
        (limit,),
    )
    return [row[0] for row in cur.fetchall()]


def build_ddl_summary(table_name, columns, pk_columns):
    lines = [f"CREATE TABLE olist.{table_name} ("]
    column_lines = [
        f"    {column_name} {data_type}"
        + ("" if is_nullable == "YES" else " NOT NULL")
        for column_name, data_type, is_nullable in columns
    ]
    if pk_columns:
        ordered_pk = [name for name, _, _ in columns if name in pk_columns]
        column_lines.append(f"    PRIMARY KEY ({', '.join(ordered_pk)})")
    lines.append(",\n".join(column_lines))
    lines.append(");")
    return "\n".join(lines)


def sync():
    conn = connect()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_DDL)
            cur.execute(
                "TRUNCATE app.catalog_columns, app.catalog_tables "
                "RESTART IDENTITY CASCADE;"
            )

            pk_by_table = primary_key_columns_by_table(cur)
            fk_by_column = foreign_keys_by_column(cur)

            for table_name in olist_table_names(cur):
                columns = olist_columns(cur, table_name)
                pk_columns = pk_by_table.get(table_name, set())
                row_count = olist_row_count(cur, table_name)
                ddl_summary = build_ddl_summary(table_name, columns, pk_columns)

                cur.execute(
                    "INSERT INTO app.catalog_tables "
                    "(table_name, description, row_count, ddl_summary) "
                    "VALUES (%s, NULL, %s, %s) RETURNING id",
                    (table_name, row_count, ddl_summary),
                )
                table_id = cur.fetchone()[0]

                for column_name, data_type, _is_nullable in columns:
                    is_pk = column_name in pk_columns
                    ref_table = fk_by_column.get((table_name, column_name))
                    is_fk = ref_table is not None
                    samples_json = json.dumps(
                        sample_values(cur, table_name, column_name), default=str
                    )
                    cur.execute(
                        "INSERT INTO app.catalog_columns "
                        "(table_id, column_name, data_type, is_pk, is_fk, "
                        "ref_table, sample_values_json) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)",
                        (
                            table_id,
                            column_name,
                            data_type,
                            is_pk,
                            is_fk,
                            ref_table,
                            samples_json,
                        ),
                    )

                print(f"  olist.{table_name}: {len(columns)} columns, {row_count} rows")

        conn.commit()
        print("Catalog sync complete.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    sync()


if __name__ == "__main__":
    main()
