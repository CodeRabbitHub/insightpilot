import sys

from dotenv import load_dotenv

from app.catalog.sync import connect
from app.glossary.embed import EMBEDDING_DIMENSION, GLOSSARY_FILE, parse_glossary_entries

load_dotenv()


def check_embeddings(cur):
    failures = []
    expected_sources = {
        source for source, _content in parse_glossary_entries(
            GLOSSARY_FILE.read_text(encoding="utf-8")
        )
    }

    cur.execute("SELECT source, vector_dims(embedding) FROM app.kb_chunks")
    rows = {source: dims for source, dims in cur.fetchall()}

    if set(rows) != expected_sources:
        missing = expected_sources - set(rows)
        extra = set(rows) - expected_sources
        print(
            f"  [FAIL] app.kb_chunks: {len(rows)} rows, expected "
            f"{len(expected_sources)} (missing={sorted(missing)}, "
            f"extra={sorted(extra)})"
        )
        failures.append("row set")

    for source in sorted(expected_sources):
        dims = rows.get(source)
        ok = dims == EMBEDDING_DIMENSION
        shown = "MISSING" if dims is None else f"{dims} dims"
        print(f"  [{'OK' if ok else 'FAIL'}] glossary.{source}: embedding={shown}")
        if not ok:
            failures.append(source)

    return failures


def main():
    conn = connect()
    try:
        with conn.cursor() as cur:
            print("Glossary embeddings:")
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
