import os
from pathlib import Path
from string import Template

from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, field_validator

from app.catalog.describe import (
    extract_json_object,
    fetch_columns,
    fetch_tables,
    format_columns_context,
)
from app.catalog.sync import connect, require_env

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROMPT_FILE = REPO_ROOT / "prompts" / "generate_sql.md"
PROMPT_TEMPLATE = Template(PROMPT_FILE.read_text(encoding="utf-8"))
DEFAULT_MODEL = "claude-sonnet-5"
MAX_RETRIES = 1

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


def build_schema_context(cur):
    blocks = []
    for table_id, table_name, description, ddl_summary in fetch_tables(cur):
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


def build_prompt(question, schema_context):
    return PROMPT_TEMPLATE.substitute(
        schema_context=schema_context,
        question=question,
    )


def call_llm_for_sql(client, model, question, schema_context):
    prompt = build_prompt(question, schema_context)
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


def generate_sql():
    api_key = require_env("ANTHROPIC_API_KEY")
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
    client = Anthropic(api_key=api_key)

    conn = connect()
    try:
        with conn.cursor() as cur:
            schema_context = build_schema_context(cur)
    finally:
        conn.close()

    return call_llm_for_sql(client, model, FIXED_QUESTION, schema_context)


def main():
    print(generate_sql())


if __name__ == "__main__":
    main()
