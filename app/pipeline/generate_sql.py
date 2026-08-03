import os
from pathlib import Path
from string import Template

import voyageai
from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, field_validator

from app.catalog.describe import (
    extract_json_object,
    fetch_columns,
    format_columns_context,
)
from app.catalog.embed import VOYAGE_MODEL, embed_text, to_vector_literal
from app.catalog.sync import connect, require_env

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROMPT_FILE = REPO_ROOT / "prompts" / "generate_sql.md"
PROMPT_TEMPLATE = Template(PROMPT_FILE.read_text(encoding="utf-8"))
DEFAULT_MODEL = "claude-sonnet-5"
MAX_RETRIES = 1
RETRIEVAL_K = 5
# Smaller than RETRIEVAL_K: 16 KPIs total (vs. 9 tables), and a question
# usually implicates 1-3 KPIs at most.
GLOSSARY_RETRIEVAL_K = 3

FIXED_QUESTION = "What are the top 5 product categories by number of orders?"


class GenerateSqlResponse(BaseModel):
    sql: str

    @field_validator("sql")
    @classmethod
    def sql_must_be_a_single_select_statement(cls, value):
        stripped = value.strip().rstrip(";").strip()
        if not stripped or not stripped.upper().startswith("SELECT"):
            raise ValueError(f"sql is not a SELECT statement: {value!r}")
        if ";" in stripped:
            raise ValueError(f"sql contains more than one statement: {value!r}")
        return stripped


def retrieve_relevant_tables(cur, voyage_client, question, k=RETRIEVAL_K):
    """Top-k (table_id, table_name, description, ddl_summary) rows, ranked
    by pgvector cosine distance between the question's embedding and each
    table's stored description embedding."""
    question_embedding = embed_text(voyage_client, VOYAGE_MODEL, question, "query")
    cur.execute(
        "SELECT ct.id, ct.table_name, ct.description, ct.ddl_summary "
        "FROM app.catalog_embeddings ce "
        "JOIN app.catalog_tables ct ON ct.id = ce.table_id "
        "ORDER BY ce.embedding <=> %s::vector "
        "LIMIT %s",
        (to_vector_literal(question_embedding), k),
    )
    return cur.fetchall()


def retrieve_relevant_glossary_entries(cur, voyage_client, question, k=GLOSSARY_RETRIEVAL_K):
    """Top-k (source, content) rows from the business glossary, ranked by
    pgvector cosine distance between the question's embedding and each
    KPI chunk's stored embedding."""
    question_embedding = embed_text(voyage_client, VOYAGE_MODEL, question, "query")
    cur.execute(
        "SELECT source, content FROM app.kb_chunks "
        "ORDER BY embedding <=> %s::vector "
        "LIMIT %s",
        (to_vector_literal(question_embedding), k),
    )
    return cur.fetchall()


def build_glossary_context(entries):
    return "\n\n".join(content for _source, content in entries)


def build_schema_context(cur, tables):
    blocks = []
    for table_id, table_name, description, ddl_summary in tables:
        if description is None:
            raise RuntimeError(
                f"olist.{table_name} has no description yet -- run "
                "`python -m app.catalog.describe` before generating SQL"
            )
        columns = fetch_columns(cur, table_id)
        blocks.append(
            f"Table: olist.{table_name}\n"
            f"Description: {description}\n"
            f"DDL:\n{ddl_summary}\n"
            f"Columns:\n{format_columns_context(columns)}"
        )
    return "\n\n".join(blocks)


def build_prompt(question, schema_context, glossary_context):
    return PROMPT_TEMPLATE.substitute(
        schema_context=schema_context,
        question=question,
        glossary_context=glossary_context,
    )


def call_llm_for_sql(client, model, question, schema_context, glossary_context):
    prompt = build_prompt(question, schema_context, glossary_context)
    last_error = None
    for attempt in range(1 + MAX_RETRIES):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            data = extract_json_object(response.content[0].text)
            validated = GenerateSqlResponse.model_validate(data)
            return validated.sql
        except Exception as exc:  # API error, json.JSONDecodeError, or ValidationError
            last_error = exc
    raise RuntimeError(
        f"LLM failed to produce a valid SELECT statement after "
        f"{1 + MAX_RETRIES} attempt(s): {last_error}"
    )


def generate_sql(question=FIXED_QUESTION):
    api_key = require_env("ANTHROPIC_API_KEY")
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
    client = Anthropic(api_key=api_key)
    voyage_client = voyageai.Client(api_key=require_env("VOYAGE_API_KEY"))

    conn = connect()
    try:
        with conn.cursor() as cur:
            # retrieve_relevant_tables and retrieve_relevant_glossary_entries
            # each embed `question` independently -- two Voyage calls per
            # question instead of one shared embedding. Deliberate: the
            # brief keeps retrieve_relevant_tables's own signature/behavior
            # out of scope, so it can't be changed to accept a pre-computed
            # embedding. Paid for via RATE_LIMIT_MAX_ATTEMPTS (see
            # app/catalog/embed.py) and the timeouts in stop_verify.py and
            # tests/_answer_helpers.py / tests/_generate_sql_helpers.py.
            tables = retrieve_relevant_tables(cur, voyage_client, question)
            schema_context = build_schema_context(cur, tables)
            glossary_entries = retrieve_relevant_glossary_entries(cur, voyage_client, question)
            glossary_context = build_glossary_context(glossary_entries)
    finally:
        conn.close()

    return call_llm_for_sql(client, model, question, schema_context, glossary_context)


def main():
    print(generate_sql())


if __name__ == "__main__":
    main()
