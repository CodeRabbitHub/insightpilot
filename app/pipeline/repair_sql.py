import os
from pathlib import Path
from string import Template

from anthropic import Anthropic
from dotenv import load_dotenv

from app.catalog.describe import extract_json_object
from app.catalog.sync import require_env
from app.pipeline.generate_sql import DEFAULT_MODEL, GenerateSqlResponse

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROMPT_FILE = REPO_ROOT / "prompts" / "repair_sql.md"
PROMPT_TEMPLATE = Template(PROMPT_FILE.read_text(encoding="utf-8"))


def build_prompt(question, failed_sql, error_message):
    return PROMPT_TEMPLATE.substitute(
        question=question, failed_sql=failed_sql, error=error_message
    )


def call_llm_for_repair(client, model, question, failed_sql, error_message):
    """One Anthropic call, no internal retry -- PRD's "max 2 attempts
    total" budgets exactly one generate call and one repair call, so a
    malformed repair response here is the final failure, not something to
    retry."""
    prompt = build_prompt(question, failed_sql, error_message)
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
        raise RuntimeError(
            f"LLM failed to produce a valid repaired SELECT statement: {exc}"
        ) from exc


def repair_sql(question, failed_sql, error_message):
    api_key = require_env("ANTHROPIC_API_KEY")
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
    client = Anthropic(api_key=api_key)
    return call_llm_for_repair(client, model, question, failed_sql, error_message)
