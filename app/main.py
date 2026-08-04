from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.pipeline.answer import get_answer

app = FastAPI()


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    sql: str
    rows: list[dict[str, Any]]


@app.post("/api/ask", response_model=AskResponse)
async def ask(request: AskRequest) -> AskResponse:
    """Interim endpoint -- PRD Sec.8's eventual shape is
    /api/conversations/{id}/messages, pending F7 conversation persistence.
    Wraps get_answer() unchanged; any failure it raises (SQL generation,
    validation, execution, or its one repair attempt) maps to 502 -- from
    this endpoint's perspective all of it is an upstream pipeline failure,
    not a bug in the transport layer."""
    try:
        sql, rows = await get_answer(request.question)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return AskResponse(sql=sql, rows=rows)
