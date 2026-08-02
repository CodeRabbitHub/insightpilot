import json
import sys

from dotenv import load_dotenv

from app.catalog.sync import (
    connect,
    foreign_keys_by_column,
    olist_columns,
    olist_row_count,
    olist_table_names,
    primary_key_columns_by_table,
    sample_values,
)

load_dotenv()


def _parse_sample_values(raw):
    if raw is None:
        return None
    if isinstance(raw, str):
        return json.loads(raw)
    return raw


def check_table_rows(cur):
    failures = []
    cur.execute("SELECT COUNT(*) FROM app.catalog_tables")
    count = cur.fetchone()[0]
    ok = count == 9
    print(f"  [{'OK' if ok else 'FAIL'}] app.catalog_tables: {count} rows (expected 9)")
    if not ok:
        failures.append("row count")

    for table_name in olist_table_names(cur):
        live_count = olist_row_count(cur, table_name)
        cur.execute(
            "SELECT row_count, ddl_summary FROM app.catalog_tables WHERE table_name = %s",
            (table_name,),
        )
        row = cur.fetchone()
        if row is None:
            print(f"  [FAIL] olist.{table_name}: no catalog_tables row")
            failures.append(table_name)
            continue
        row_count, ddl_summary = row
        ok = row_count == live_count and bool(ddl_summary and ddl_summary.strip())
        print(
            f"  [{'OK' if ok else 'FAIL'}] olist.{table_name}: row_count={row_count} "
            f"(expected {live_count}), ddl_summary={'set' if ddl_summary else 'EMPTY'}"
        )
        if not ok:
            failures.append(table_name)
    return failures


def check_columns(cur):
    failures = []
    for table_name in olist_table_names(cur):
        live_cols = {name for name, _, _ in olist_columns(cur, table_name)}
        cur.execute(
            "SELECT cc.column_name FROM app.catalog_columns cc "
            "JOIN app.catalog_tables ct ON cc.table_id = ct.id "
            "WHERE ct.table_name = %s",
            (table_name,),
        )
        catalog_cols = {row[0] for row in cur.fetchall()}
        ok = catalog_cols == live_cols
        print(f"  [{'OK' if ok else 'FAIL'}] olist.{table_name}: {len(catalog_cols)} columns")
        if not ok:
            failures.append(table_name)
    return failures


def check_primary_keys(cur):
    failures = []
    pk_by_table = primary_key_columns_by_table(cur)
    cur.execute(
        "SELECT ct.table_name, cc.column_name, cc.is_pk "
        "FROM app.catalog_columns cc "
        "JOIN app.catalog_tables ct ON cc.table_id = ct.id"
    )
    for table_name, column_name, is_pk in cur.fetchall():
        expected = column_name in pk_by_table.get(table_name, set())
        ok = is_pk == expected
        if not ok:
            print(
                f"  [FAIL] {table_name}.{column_name}: is_pk={is_pk} "
                f"(expected {expected})"
            )
            failures.append(f"{table_name}.{column_name}")
    print(f"  [{'OK' if not failures else 'FAIL'}] primary keys match live introspection")
    return failures


def check_foreign_keys(cur):
    failures = []
    fk_by_column = foreign_keys_by_column(cur)
    cur.execute(
        "SELECT ct.table_name, cc.column_name, cc.is_fk, cc.ref_table "
        "FROM app.catalog_columns cc "
        "JOIN app.catalog_tables ct ON cc.table_id = ct.id"
    )
    for table_name, column_name, is_fk, ref_table in cur.fetchall():
        expected_ref = fk_by_column.get((table_name, column_name))
        ok = is_fk == (expected_ref is not None) and ref_table == expected_ref
        if not ok:
            print(
                f"  [FAIL] {table_name}.{column_name}: is_fk={is_fk}, "
                f"ref_table={ref_table} (expected is_fk={expected_ref is not None}, "
                f"ref_table={expected_ref})"
            )
            failures.append(f"{table_name}.{column_name}")
    print(f"  [{'OK' if not failures else 'FAIL'}] foreign keys match live introspection")
    return failures


def check_sample_values(cur):
    failures = []
    for table_name in olist_table_names(cur):
        for column_name, _data_type, _is_nullable in olist_columns(cur, table_name):
            expected = [str(v) for v in sample_values(cur, table_name, column_name)]
            cur.execute(
                "SELECT cc.sample_values_json FROM app.catalog_columns cc "
                "JOIN app.catalog_tables ct ON cc.table_id = ct.id "
                "WHERE ct.table_name = %s AND cc.column_name = %s",
                (table_name, column_name),
            )
            row = cur.fetchone()
            actual_raw = _parse_sample_values(row[0]) if row else None
            actual = [str(v) for v in actual_raw] if actual_raw is not None else None
            ok = (
                actual is not None
                and actual == expected
                and len(actual) == len(set(actual))
                and len(actual) <= 5
            )
            if not ok:
                print(
                    f"  [FAIL] {table_name}.{column_name}: sample_values_json="
                    f"{actual} (expected {expected})"
                )
                failures.append(f"{table_name}.{column_name}")
    print(f"  [{'OK' if not failures else 'FAIL'}] sample values match live introspection")
    return failures


def main():
    conn = connect()
    try:
        with conn.cursor() as cur:
            print("Table rows:")
            table_failures = check_table_rows(cur)
            print("Columns:")
            column_failures = check_columns(cur)
            print("Primary keys:")
            pk_failures = check_primary_keys(cur)
            print("Foreign keys:")
            fk_failures = check_foreign_keys(cur)
            print("Sample values:")
            sample_failures = check_sample_values(cur)
    finally:
        conn.close()

    all_failures = (
        table_failures + column_failures + pk_failures + fk_failures + sample_failures
    )
    if all_failures:
        print("\nverify_sync: FAILED")
        sys.exit(1)

    print("\nverify_sync: PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
