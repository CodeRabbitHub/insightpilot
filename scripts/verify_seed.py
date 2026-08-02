import csv
import sys

import psycopg2
from dotenv import load_dotenv

from seed import TABLES, DATA_DIR, connect, require_env

load_dotenv()


def csv_row_count(csv_name):
    # Some columns (e.g. review_comment_message) contain embedded newlines
    # inside quoted fields, so a raw line count overcounts rows — the csv
    # module is required to parse quoting correctly.
    csv_path = DATA_DIR / csv_name
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        return sum(1 for _ in csv.reader(f)) - 1  # exclude header row


def check_row_counts(cur):
    failures = []
    for csv_name, table_name, _ddl in TABLES:
        expected = csv_row_count(csv_name)
        cur.execute(f"SELECT COUNT(*) FROM olist.{table_name};")
        actual = cur.fetchone()[0]
        ok = actual == expected
        print(f"  [{'OK' if ok else 'FAIL'}] olist.{table_name}: {actual} rows (expected {expected})")
        if not ok:
            failures.append(table_name)
    return failures


def check_vector_extension(cur):
    cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector';")
    ok = cur.fetchone() is not None
    print(f"  [{'OK' if ok else 'FAIL'}] vector extension installed")
    return ok


def check_ro_permissions():
    ro_user = require_env("OLIST_RO_USER")
    probe_table = TABLES[0][1]
    ro_conn = connect(user_env="OLIST_RO_USER", password_env="OLIST_RO_PASSWORD")
    ro_conn.autocommit = False
    ok = False
    try:
        with ro_conn.cursor() as cur:
            try:
                cur.execute(
                    f"INSERT INTO olist.{probe_table} DEFAULT VALUES;"
                )
            except psycopg2.errors.InsufficientPrivilege:
                ok = True
            finally:
                ro_conn.rollback()
    finally:
        ro_conn.close()
    print(f"  [{'OK' if ok else 'FAIL'}] {ro_user} denied INSERT (permissions enforced)")
    return ok


def main():
    conn = connect()
    try:
        with conn.cursor() as cur:
            print("Row counts:")
            row_count_failures = check_row_counts(cur)
            print("Extensions:")
            vector_ok = check_vector_extension(cur)
    finally:
        conn.close()

    print("Permissions:")
    ro_ok = check_ro_permissions()

    if row_count_failures or not vector_ok or not ro_ok:
        print("\nverify_seed: FAILED")
        sys.exit(1)

    print("\nverify_seed: PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
