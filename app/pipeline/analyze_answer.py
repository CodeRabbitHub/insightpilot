import json
import os
from pathlib import Path
from string import Template
from typing import Any

from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, field_validator

from app.catalog.describe import extract_json_object
from app.catalog.sync import require_env
from app.pipeline.generate_sql import DEFAULT_MODEL, MAX_RETRIES

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROMPT_FILE = REPO_ROOT / "prompts" / "analyze.md"
PROMPT_TEMPLATE = Template(PROMPT_FILE.read_text(encoding="utf-8"))

# Smaller than PRD F1's 50-row display cap -- a ceiling, not a target --
# keeps prompt tokens bounded regardless of execute_sql()'s up-to-1000-row
# result.
ROW_SAMPLE_CAP = 20


class AnalyzeResponse(BaseModel):
    summary: str
    explanation: str
    chart_spec: dict[str, Any]
    follow_ups: list[str]

    @field_validator("summary", "explanation")
    @classmethod
    def must_be_nonblank(cls, value):
        if not value.strip():
            raise ValueError("must be a non-blank string")
        return value

    @field_validator("follow_ups")
    @classmethod
    def must_be_nonempty_nonblank_strings(cls, value):
        if not value:
            raise ValueError("follow_ups must be a non-empty list")
        if any(not item.strip() for item in value):
            raise ValueError("follow_ups must not contain blank strings")
        return value


def build_prompt(question, sql, rows):
    sample = rows[:ROW_SAMPLE_CAP]
    return PROMPT_TEMPLATE.substitute(
        question=question,
        sql=sql,
        row_count=len(rows),
        sample_size=len(sample),
        row_sample=json.dumps(sample, default=str),
    )


def _extract_response_text(response):
    # response.content[0] is not always the text block -- Claude can
    # prepend a ThinkingBlock (no .text attribute) ahead of the TextBlock,
    # observed for real against this prompt during this slice's own gate.
    for block in response.content:
        if getattr(block, "type", None) == "text":
            return block.text
    raise RuntimeError("Anthropic response contained no text content block")


def call_llm_for_analysis(client, model, question, sql, rows):
    prompt = build_prompt(question, sql, rows)
    last_error = None
    for attempt in range(1 + MAX_RETRIES):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=1536,
                messages=[{"role": "user", "content": prompt}],
            )
            data = extract_json_object(_extract_response_text(response))
            return AnalyzeResponse.model_validate(data)
        except Exception as exc:  # API error, json.JSONDecodeError, or ValidationError
            last_error = exc
    raise RuntimeError(
        f"LLM failed to produce a valid analysis after "
        f"{1 + MAX_RETRIES} attempt(s): {last_error}"
    )


def analyze_answer(question, sql, rows):
    api_key = require_env("ANTHROPIC_API_KEY")
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
    client = Anthropic(api_key=api_key)
    return call_llm_for_analysis(client, model, question, sql, rows)
