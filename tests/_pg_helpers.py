"""
Shared helpers for the foundation-db-seed integration tests.

Not a test module itself (unittest discover only picks up test_*.py), just
connection/CSV plumbing shared by the real test files.

Connection info is read from environment variables, falling back to a
`.env` file at the repo root (same convention the brief says seed/verify
scripts will use), falling back to defaults that match common Postgres
docker-compose setups. Real env vars always win over `.env` file values.

Expected variable names:
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER,
    POSTGRES_PASSWORD          -- admin/superuser connection
    OLIST_RO_USER, OLIST_RO_PASSWORD  -- the read-only role under test
"""
import csv
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
ENV_FILE = REPO_ROOT / ".env"

_DEFAULTS = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "insightpilot",
    "POSTGRES_USER": "postgres",
    "POSTGRES_PASSWORD": "postgres",
    "OLIST_RO_USER": "olist_ro",
    "OLIST_RO_PASSWORD": "olist_ro_password",
}


def _load_dotenv_once():
    if not ENV_FILE.exists():
        return
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv_once()
for _key, _default in _DEFAULTS.items():
    os.environ.setdefault(_key, _default)


def conn_params():
    return {
        "host": os.environ["POSTGRES_HOST"],
        "port": os.environ["POSTGRES_PORT"],
        "dbname": os.environ["POSTGRES_DB"],
        "user": os.environ["POSTGRES_USER"],
        "password": os.environ["POSTGRES_PASSWORD"],
    }


def ro_conn_params():
    params = conn_params()
    params["user"] = os.environ["OLIST_RO_USER"]
    params["password"] = os.environ["OLIST_RO_PASSWORD"]
    return params


def get_admin_connection():
    import psycopg2

    return psycopg2.connect(**conn_params())


def get_ro_connection():
    import psycopg2

    return psycopg2.connect(**ro_conn_params())


def all_csv_files():
    files = sorted(DATA_DIR.glob("*.csv"))
    return files


def csv_data_row_count(csv_path: Path) -> int:
    """Row count excluding the header line, using csv.reader so quoted
    newlines inside fields (e.g. review comments) don't inflate the count."""
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        rows = sum(1 for _ in reader)
    return max(rows - 1, 0)


def expected_row_counts():
    """Sorted list of expected per-table row counts, derived live from the
    CSVs in data/ -- never hardcoded, per the brief's done-check wording."""
    return sorted(csv_data_row_count(f) for f in all_csv_files())


def olist_table_names(cursor):
    cursor.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = %s AND table_type = 'BASE TABLE'",
        ("olist",),
    )
    return [row[0] for row in cursor.fetchall()]


def olist_table_row_counts(cursor):
    import psycopg2.sql as sql

    counts = []
    for table_name in olist_table_names(cursor):
        cursor.execute(
            sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
                sql.Identifier("olist"), sql.Identifier(table_name)
            )
        )
        counts.append(cursor.fetchone()[0])
    return sorted(counts)
