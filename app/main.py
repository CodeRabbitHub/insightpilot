import json
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.db.models import Conversation, Message
from app.db.session import async_session_factory
from app.pipeline.answer import get_answer

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    sql: str
    rows: list[dict[str, Any]]


class CreateConversationResponse(BaseModel):
    id: int


class ConversationMessageResult(BaseModel):
    conversation_id: int
    message_id: int
    sql: str
    rows: list[dict[str, Any]]


class ConversationSummary(BaseModel):
    id: int
    title: str | None
    created_at: datetime


class MessageDetail(BaseModel):
    id: int
    role: str
    content_json: dict[str, Any]
    created_at: datetime


class ConversationDetail(BaseModel):
    id: int
    title: str | None
    created_at: datetime
    messages: list[MessageDetail]


async def _persist_exchange(question: str, response: AskResponse) -> None:
    """Persist one Conversation plus its user/assistant Message pair
    through app/db's pool -- called only after get_answer() has already
    succeeded, never on the failure path. Not wrapped in its own
    try/except: a write failure here is a real app-DB error, distinct
    from get_answer()'s 502-mapped pipeline failures, so it is left to
    surface as an uncaught error rather than being folded into that
    contract."""
    async with async_session_factory() as session:
        conversation = Conversation()
        session.add(conversation)
        await session.flush()
        session.add(
            Message(
                conversation_id=conversation.id,
                role="user",
                content_json={"question": question},
            )
        )
        session.add(
            Message(
                conversation_id=conversation.id,
                role="assistant",
                content_json=jsonable_encoder(response),
            )
        )
        await session.commit()


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
    response = AskResponse(sql=sql, rows=rows)
    await _persist_exchange(request.question, response)
    return response


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
    await _persist_exchange(question, response)
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


@app.post("/api/conversations", response_model=CreateConversationResponse)
async def create_conversation() -> CreateConversationResponse:
    """PRD.md Sec.8's real conversation-creation endpoint -- unlike
    _persist_exchange(), which creates a Conversation implicitly as a
    side effect of answering a question, this creates one explicitly and
    empty, so a client can hold its id across multiple later messages."""
    async with async_session_factory() as session:
        conversation = Conversation()
        session.add(conversation)
        await session.flush()
        conversation_id = conversation.id
        await session.commit()
    return CreateConversationResponse(id=conversation_id)


async def _persist_message_pair(
    conversation_id: int, question: str, response: AskResponse
) -> int:
    """Persist a user/assistant Message pair under an EXISTING
    conversation -- unlike _persist_exchange(), which always creates a
    brand-new Conversation. Returns the assistant message's id so the
    caller can include it in the SSE result event. Not wrapped in its
    own try/except, for the same reason as _persist_exchange(): a write
    failure here is a real app-DB error, left to surface uncaught rather
    than folded into get_answer()'s pipeline-failure contract."""
    async with async_session_factory() as session:
        session.add(
            Message(
                conversation_id=conversation_id,
                role="user",
                content_json={"question": question},
            )
        )
        assistant_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content_json=jsonable_encoder(response),
        )
        session.add(assistant_message)
        await session.flush()
        message_id = assistant_message.id
        await session.commit()
    return message_id


async def _conversation_message_stream_events(conversation_id: int, question: str):
    """Same eventual-outcome-only SSE shape as _ask_stream_events(), but
    persisting against an existing conversation_id and including it plus
    the new message_id in the result event, per PRD.md Sec.8. Mirrors
    _ask_stream_events()'s try/except/yield structure deliberately rather
    than extracting a shared helper -- /api/ask/stream must stay
    byte-for-byte unchanged this slice, so its generator is left
    untouched rather than refactored to share code with this one."""
    try:
        sql, rows = await get_answer(question)
    except Exception as exc:
        payload = json.dumps({"detail": str(exc)})
        yield f"event: error\ndata: {payload}\n\n"
        return
    response = AskResponse(sql=sql, rows=rows)
    message_id = await _persist_message_pair(conversation_id, question, response)
    result = ConversationMessageResult(
        conversation_id=conversation_id,
        message_id=message_id,
        sql=response.sql,
        rows=response.rows,
    )
    payload = json.dumps(jsonable_encoder(result))
    yield f"event: result\ndata: {payload}\n\n"


@app.post("/api/conversations/{conversation_id}/messages")
async def post_conversation_message(
    conversation_id: int, request: AskRequest
) -> StreamingResponse:
    """Checks conversation_id exists before calling get_answer() at all --
    an unknown id must 404 with zero LLM calls and nothing persisted,
    never waste a real Anthropic call validating a path parameter."""
    async with async_session_factory() as session:
        conversation = await session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    return StreamingResponse(
        _conversation_message_stream_events(conversation_id, request.question),
        media_type="text/event-stream",
    )


@app.get("/api/conversations", response_model=list[ConversationSummary])
async def list_conversations() -> list[ConversationSummary]:
    """PRD.md Sec.8's list endpoint -- every conversation, newest first.
    `id` is included as a tiebreaker alongside `created_at` so ordering
    stays deterministic even for rows created within the same instant."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Conversation).order_by(
                Conversation.created_at.desc(), Conversation.id.desc()
            )
        )
        conversations = result.scalars().all()
    return [
        ConversationSummary(id=c.id, title=c.title, created_at=c.created_at)
        for c in conversations
    ]


@app.get("/api/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: int) -> ConversationDetail:
    """PRD.md Sec.8's detail endpoint -- one conversation plus its
    messages in chronological (oldest-first) order, 404 on an unknown id."""
    async with async_session_factory() as session:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="conversation not found")
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id)
        )
        messages = result.scalars().all()
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        messages=[
            MessageDetail(
                id=m.id,
                role=m.role,
                content_json=m.content_json,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )
