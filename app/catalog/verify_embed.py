import sys

from dotenv import load_dotenv

from app.catalog.embed import EMBEDDING_DIMENSION
from app.catalog.sync import connect

load_dotenv()


def check_embeddings(cur):
    failures = []
    cur.execute(
        "SELECT ct.table_name, ce.table_id, vector_dims(ce.embedding) "
        "FROM app.catalog_tables ct "
        "LEFT JOIN app.catalog_embeddings ce ON ce.table_id = ct.id "
        "ORDER BY ct.table_name"
    )
    rows = cur.fetchall()
    if len(rows) != 9:
        print(f"  [FAIL] app.catalog_tables: {len(rows)} rows (expected 9)")
        failures.append("row count")

    for table_name, table_id, dims in rows:
        ok = table_id is not None and dims == EMBEDDING_DIMENSION
        shown = "MISSING" if table_id is None else f"{dims} dims"
        print(f"  [{'OK' if ok else 'FAIL'}] olist.{table_name}: embedding={shown}")
        if not ok:
            failures.append(table_name)
    return failures


def main():
    conn = connect()
    try:
        with conn.cursor() as cur:
            print("Embeddings:")
            failures = check_embeddings(cur)
    finally:
        conn.close()

    if failures:
        print("\nverify_embed: FAILED")
        sys.exit(1)

    print("\nverify_embed: PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
