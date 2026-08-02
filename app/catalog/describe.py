import json
import os
from pathlib import Path
from string import Template

from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, field_validator

from app.catalog.sync import connect, require_env

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROMPT_FILE = REPO_ROOT / "prompts" / "table_description.md"
PROMPT_TEMPLATE = Template(PROMPT_FILE.read_text(encoding="utf-8"))
DEFAULT_MODEL = "claude-sonnet-5"
MIN_DESCRIPTION_WORDS = 20
MAX_RETRIES = 1


def is_genuine_paragraph(text):
    """True if text reads as a real paragraph, not a blank/stub response.

    Shared between TableDescriptionResponse's validator and
    verify_describe.py, so "what counts as a real description" is defined
    in exactly one place.
    """
    if text is None:
        return False
    stripped = text.strip()
    if not stripped:
        return False
    return len(stripped.split()) >= MIN_DESCRIPTION_WORDS


class TableDescriptionResponse(BaseModel):
    description: str

    @field_validator("description")
    @classmethod
    def description_must_be_a_genuine_paragraph(cls, value):
        if not is_genuine_paragraph(value):
            raise ValueError(
                f"description is not a genuine paragraph (need at least "
                f"{MIN_DESCRIPTION_WORDS} words): {value!r}"
            )
        return value.strip()


def format_columns_context(columns):
    lines = []
    for column_name, data_type, is_pk, is_fk, ref_table, sample_values_json in columns:
        flags = []
        if is_pk:
            flags.append("PK")
        if is_fk:
            flags.append(f"FK -> {ref_table}")
        flag_text = f" [{', '.join(flags)}]" if flags else ""
        samples = json.loads(sample_values_json) if isinstance(
            sample_values_json, str
        ) else sample_values_json
        lines.append(
            f"- {column_name} ({data_type}){flag_text}: sample values = {samples}"
        )
    return "\n".join(lines)


def build_prompt(table_name, ddl_summary, columns):
    return PROMPT_TEMPLATE.substitute(
        table_name=table_name,
        ddl_summary=ddl_summary,
        columns_context=format_columns_context(columns),
    )


def extract_json_object(text):
    """Parse the model's reply as a JSON object, tolerating a leading/
    trailing markdown code fence around an otherwise-bare JSON object."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:]
        stripped = stripped.strip()
    return json.loads(stripped)


def call_llm_for_description(client, model, table_name, ddl_summary, columns):
    prompt = build_prompt(table_name, ddl_summary, columns)
    last_error = None
    for attempt in range(1 + MAX_RETRIES):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            data = extract_json_object(response.content[0].text)
            validated = TableDescriptionResponse.model_validate(data)
            return validated.description
        except Exception as exc:  # API error, json.JSONDecodeError, or ValidationError
            last_error = exc
    raise RuntimeError(
        f"olist.{table_name}: LLM failed to produce a valid description "
        f"after {1 + MAX_RETRIES} attempt(s): {last_error}"
    )


def fetch_tables(cur):
    cur.execute(
        "SELECT id, table_name, description, ddl_summary FROM app.catalog_tables "
        "ORDER BY table_name"
    )
    return cur.fetchall()


def fetch_columns(cur, table_id):
    cur.execute(
        "SELECT column_name, data_type, is_pk, is_fk, ref_table, sample_values_json "
        "FROM app.catalog_columns WHERE table_id = %s ORDER BY id",
        (table_id,),
    )
    return cur.fetchall()


def describe():
    api_key = require_env("ANTHROPIC_API_KEY")
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
    client = Anthropic(api_key=api_key)

    conn = connect()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            tables = fetch_tables(cur)

        for table_id, table_name, description, ddl_summary in tables:
            if description is not None:
                print(f"  olist.{table_name}: already described, skipping")
                continue

            with conn.cursor() as cur:
                columns = fetch_columns(cur, table_id)

            new_description = call_llm_for_description(
                client, model, table_name, ddl_summary, columns
            )

            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE app.catalog_tables SET description = %s WHERE id = %s",
                    (new_description, table_id),
                )
            conn.commit()
            print(f"  olist.{table_name}: described ({len(new_description)} chars)")

        print("Table description sync complete.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    describe()


if __name__ == "__main__":
    main()
