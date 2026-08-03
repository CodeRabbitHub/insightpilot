import re
from pathlib import Path

import voyageai
from dotenv import load_dotenv

from app.catalog.embed import EMBEDDING_DIMENSION, VOYAGE_MODEL, embed_text, to_vector_literal
from app.catalog.sync import connect, require_env

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GLOSSARY_FILE = REPO_ROOT / "glossary.md"

SCHEMA_DDL = f"""
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS app.kb_chunks (
    id SERIAL PRIMARY KEY,
    source TEXT UNIQUE NOT NULL,
    content TEXT NOT NULL,
    embedding vector({EMBEDDING_DIMENSION}) NOT NULL
);
"""

_HEADING_RE = re.compile(r"(?m)^## (.+)$")


def _slugify(heading):
    slug = heading.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def parse_glossary_entries(text):
    """One (source, content) tuple per `## <KPI name>` section: source is
    a stable slug of the heading, content is the full section text
    (heading included) up to the next `## ` heading or end of file."""
    matches = list(_HEADING_RE.finditer(text))
    entries = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        source = _slugify(match.group(1))
        content = text[start:end].strip()
        entries.append((source, content))
    return entries


def fetch_embedded_sources(cur):
    cur.execute("SELECT source FROM app.kb_chunks")
    return {row[0] for row in cur.fetchall()}


def embed():
    api_key = require_env("VOYAGE_API_KEY")
    client = voyageai.Client(api_key=api_key)

    entries = parse_glossary_entries(GLOSSARY_FILE.read_text(encoding="utf-8"))

    conn = connect()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_DDL)
            already_embedded = fetch_embedded_sources(cur)
        conn.commit()

        for source, content in entries:
            if source in already_embedded:
                print(f"  glossary.{source}: already embedded, skipping")
                continue

            embedding = embed_text(client, VOYAGE_MODEL, content, "document")

            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO app.kb_chunks (source, content, embedding) "
                    "VALUES (%s, %s, %s::vector) "
                    "ON CONFLICT (source) DO UPDATE SET "
                    "content = EXCLUDED.content, embedding = EXCLUDED.embedding",
                    (source, content, to_vector_literal(embedding)),
                )
            # Commit per row, not once at the end: embedding is a billed
            # external API call, so a mid-run crash must not force
            # re-embedding chunks already paid for and stored.
            conn.commit()
            print(f"  glossary.{source}: embedded ({len(embedding)} dims)")

        print("Glossary embedding sync complete.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    embed()


if __name__ == "__main__":
    main()
