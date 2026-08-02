import time

import voyageai
from dotenv import load_dotenv
from voyageai.error import RateLimitError

from app.catalog.describe import fetch_tables
from app.catalog.sync import connect, require_env

load_dotenv()

SCHEMA_DDL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS app.catalog_embeddings (
    table_id INTEGER PRIMARY KEY REFERENCES app.catalog_tables(id),
    embedding vector(1024) NOT NULL
);
"""

VOYAGE_MODEL = "voyage-3.5"
EMBEDDING_DIMENSION = 1024

# Voyage's free tier caps this project's account at 3 requests/minute.
# voyageai's own client already retries a RateLimitError a few times
# internally before giving up, so a further immediate retry on our end
# would just repeat the same failure -- only a real wait for the rate
# window to clear (~20s per allowed slot) gives a retry a chance to
# succeed.
RATE_LIMIT_MAX_ATTEMPTS = 4
RATE_LIMIT_RETRY_DELAY_SECONDS = 20


def to_vector_literal(embedding):
    """Format a list of floats as a pgvector text literal, e.g. '[0.1,0.2]'.

    Fixed-decimal formatting (not repr()/str()) avoids scientific notation
    ever landing in the literal.
    """
    return "[" + ",".join(f"{value:.8f}" for value in embedding) + "]"


def embed_text(client, model, text, input_type):
    last_error = None
    for attempt in range(RATE_LIMIT_MAX_ATTEMPTS):
        try:
            result = client.embed([text], model=model, input_type=input_type)
            return result.embeddings[0]
        except RateLimitError as exc:
            last_error = exc
            if attempt < RATE_LIMIT_MAX_ATTEMPTS - 1:
                time.sleep(RATE_LIMIT_RETRY_DELAY_SECONDS)
    raise RuntimeError(
        f"Voyage embedding call still rate-limited after "
        f"{RATE_LIMIT_MAX_ATTEMPTS} attempts, waiting "
        f"{RATE_LIMIT_RETRY_DELAY_SECONDS}s between each: {last_error}"
    )


def fetch_embedded_table_ids(cur):
    cur.execute("SELECT table_id FROM app.catalog_embeddings")
    return {row[0] for row in cur.fetchall()}


def embed():
    api_key = require_env("VOYAGE_API_KEY")
    client = voyageai.Client(api_key=api_key)

    conn = connect()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_DDL)
            tables = fetch_tables(cur)
            already_embedded = fetch_embedded_table_ids(cur)
        conn.commit()

        for table_id, table_name, description, _ddl_summary in tables:
            if table_id in already_embedded:
                print(f"  olist.{table_name}: already embedded, skipping")
                continue

            if description is None:
                raise RuntimeError(
                    f"olist.{table_name} has no description yet -- run "
                    "`python -m app.catalog.describe` before embedding"
                )

            embedding = embed_text(client, VOYAGE_MODEL, description, "document")

            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO app.catalog_embeddings (table_id, embedding) "
                    "VALUES (%s, %s::vector) "
                    "ON CONFLICT (table_id) DO UPDATE SET embedding = EXCLUDED.embedding",
                    (table_id, to_vector_literal(embedding)),
                )
            # Commit per row, not once at the end like sync.py: embedding is
            # a billed external API call, so a mid-run crash must not force
            # re-embedding tables already paid for and stored.
            conn.commit()
            print(f"  olist.{table_name}: embedded ({len(embedding)} dims)")

        print("Embedding sync complete.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    embed()


if __name__ == "__main__":
    main()
