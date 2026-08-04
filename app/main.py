import json
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
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


async def _ask_stream_events(question: str):
    """Run get_answer() once and yield its single eventual outcome as
    one SSE event -- 'result' on success, 'error' on failure. Unlike
    /api/ask, the HTTP status is always 200: once the stream has
    started, there is no later status code to change, so failure is
    signaled by the event type instead."""
    try:
        sql, rows = await get_answer(question)
    except Exception as exc:
        payload = json.dumps({"detail": str(exc)})
        yield f"event: error\ndata: {payload}\n\n"
        return
    # Routed through AskResponse, same as /api/ask, so both endpoints
    # validate get_answer()'s output against the same shape rather than
    # this route trusting an unvalidated dict.
    response = AskResponse(sql=sql, rows=rows)
    payload = json.dumps(jsonable_encoder(response))
    yield f"event: result\ndata: {payload}\n\n"


@app.post("/api/ask/stream")
async def ask_stream(request: AskRequest) -> StreamingResponse:
    """Interim SSE endpoint proving ARCHITECT.md's SSE-not-WebSockets
    transport decision. get_answer() exposes no intermediate progress
    hooks, so this streams exactly one eventual-outcome event, not real
    per-stage or per-token progress."""
    return StreamingResponse(
        _ask_stream_events(request.question), media_type="text/event-stream"
    )
