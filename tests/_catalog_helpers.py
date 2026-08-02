"""
Shared helpers for the catalog-sync-cli tests (test_catalog_sync.py,
test_verify_sync_script.py).

Reuses the connection plumbing from _pg_helpers.py (env vars / .env
loading) without modifying it. Adds catalog-specific pieces: CLI
invocation matching the brief's exact commands (`python -m
app.catalog.sync`, `python -m app.catalog.verify_sync`), and live
introspection of columns / primary keys / foreign keys / sample values in
the `olist` schema so test assertions never hardcode the schema's shape.
"""
import subprocess
import sys

import psycopg2.sql as sql

from _pg_helpers import REPO_ROOT

SYNC_TIMEOUT_SECONDS = 300
VERIFY_TIMEOUT_SECONDS = 120


def run_sync():
    return subprocess.run(
        [sys.executable, "-m", "app.catalog.sync"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=SYNC_TIMEOUT_SECONDS,
    )


def run_verify_sync():
    return subprocess.run(
        [sys.executable, "-m", "app.catalog.verify_sync"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=VERIFY_TIMEOUT_SECONDS,
    )


def olist_columns(cursor, table_name):
    """Live (column_name, data_type) pairs for one olist table, ordinal order."""
    cursor.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s "
        "ORDER BY ordinal_position",
        ("olist", table_name),
    )
    return cursor.fetchall()


def live_primary_key_columns(cursor):
    """Set of (table_name, column_name) live primary-key columns in olist."""
    cursor.execute(
        "SELECT tc.table_name, kcu.column_name "
        "FROM information_schema.table_constraints tc "
        "JOIN information_schema.key_column_usage kcu "
        "  ON tc.constraint_name = kcu.constraint_name "
        "  AND tc.table_schema = kcu.table_schema "
        "WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_schema = 'olist'"
    )
    return {(row[0], row[1]) for row in cursor.fetchall()}


def live_foreign_key_columns(cursor):
    """Dict (table_name, column_name) -> ref_table for live FK columns in olist.

    The currently-seeded olist schema has no FK constraints (documented in
    HANDOFF.md), so this is expected to return {} today -- callers should
    still compare against it rather than hardcoding "always false", so a
    future regression (or a future schema with real FKs) is still caught.
    """
    cursor.execute(
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
    return {(row[0], row[1]): row[2] for row in cursor.fetchall()}


def live_distinct_sample_values(cursor, table_name, column_name, limit=5):
    cursor.execute(
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
    return [row[0] for row in cursor.fetchall()]


_NUMERIC_TYPES = {"integer", "bigint", "smallint", "numeric", "double precision", "real"}
_TEXT_TYPES = {"text", "character varying", "character"}
_TIMESTAMP_TYPES = {"timestamp without time zone", "timestamp with time zone", "date"}


def pick_representative_columns(cursor):
    """One (table, column) pair per broad data-type category, picked live
    from information_schema so the sample_values assertions cover text,
    numeric, and timestamp columns without hardcoding olist's schema."""
    cursor.execute(
        "SELECT table_name, column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = 'olist' ORDER BY table_name, ordinal_position"
    )
    rows = cursor.fetchall()

    picked = {}
    for table_name, column_name, data_type in rows:
        if data_type in _TEXT_TYPES and "text" not in picked:
            picked["text"] = (table_name, column_name)
        elif data_type in _NUMERIC_TYPES and "numeric" not in picked:
            picked["numeric"] = (table_name, column_name)
        elif data_type in _TIMESTAMP_TYPES and "timestamp" not in picked:
            picked["timestamp"] = (table_name, column_name)
    return picked
