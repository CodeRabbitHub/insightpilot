import sys

from dotenv import load_dotenv

from app.catalog.describe import is_genuine_paragraph
from app.catalog.sync import connect

load_dotenv()


def check_descriptions(cur):
    failures = []
    cur.execute(
        "SELECT table_name, description FROM app.catalog_tables ORDER BY table_name"
    )
    rows = cur.fetchall()
    if len(rows) != 9:
        print(f"  [FAIL] app.catalog_tables: {len(rows)} rows (expected 9)")
        failures.append("row count")

    for table_name, description in rows:
        ok = is_genuine_paragraph(description)
        shown = "EMPTY" if not description else f"{len(description.strip())} chars"
        print(f"  [{'OK' if ok else 'FAIL'}] olist.{table_name}: description={shown}")
        if not ok:
            failures.append(table_name)
    return failures


def main():
    conn = connect()
    try:
        with conn.cursor() as cur:
            print("Descriptions:")
            failures = check_descriptions(cur)
    finally:
        conn.close()

    if failures:
        print("\nverify_describe: FAILED")
        sys.exit(1)

    print("\nverify_describe: PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
