import json
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.db.models import Conversation, Dashboard, DashboardCard, Message
from app.db.session import async_session_factory
from app.pipeline.analyze_answer import AnalyzeResponse
from app.pipeline.answer import _validate_and_execute, get_answer

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
    analysis: AnalyzeResponse


class CreateConversationResponse(BaseModel):
    id: int


class ConversationMessageResult(BaseModel):
    conversation_id: int
    message_id: int
    sql: str
    rows: list[dict[str, Any]]
    analysis: AnalyzeResponse


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


class CreateDashboardCardRequest(BaseModel):
    title: str
    question_text: str
    sql_text: str
    chart_spec_json: dict[str, Any]
    position: int


class DashboardCardDetail(BaseModel):
    id: int
    dashboard_id: int
    title: str
    question_text: str
    sql_text: str
    chart_spec_json: dict[str, Any]
    position: int
    created_at: datetime


class DashboardCardWithRows(DashboardCardDetail):
    rows: list[dict[str, Any]]


class DashboardDetail(BaseModel):
    id: int
    name: str
    created_at: datetime
    cards: list[DashboardCardWithRows]


class PatchDashboardCardRequest(BaseModel):
    title: str | None = None
    position: int | None = None


def _card_to_detail(card: DashboardCard) -> DashboardCardDetail:
    return DashboardCardDetail(
        id=card.id,
        dashboard_id=card.dashboard_id,
        title=card.title,
        question_text=card.question_text,
        sql_text=card.sql_text,
        chart_spec_json=card.chart_spec_json,
        position=card.position,
        created_at=card.created_at,
    )


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
        sql, rows, analysis = await get_answer(request.question)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    response = AskResponse(sql=sql, rows=rows, analysis=analysis)
    await _persist_exchange(request.question, response)
    return response


async def _ask_stream_events(question: str):
    """Run get_answer() once and yield its single eventual outcome as
    one SSE event -- 'result' on success, 'error' on failure. Unlike
    /api/ask, the HTTP status is always 200: once the stream has
    started, there is no later status code to change, so failure is
    signaled by the event type instead."""
    try:
        sql, rows, analysis = await get_answer(question)
    except Exception as exc:
        payload = json.dumps({"detail": str(exc)})
        yield f"event: error\ndata: {payload}\n\n"
        return
    # Routed through AskResponse, same as /api/ask, so both endpoints
    # validate get_answer()'s output against the same shape rather than
    # this route trusting an unvalidated dict.
    response = AskResponse(sql=sql, rows=rows, analysis=analysis)
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
        sql, rows, analysis = await get_answer(question)
    except Exception as exc:
        payload = json.dumps({"detail": str(exc)})
        yield f"event: error\ndata: {payload}\n\n"
        return
    response = AskResponse(sql=sql, rows=rows, analysis=analysis)
    message_id = await _persist_message_pair(conversation_id, question, response)
    result = ConversationMessageResult(
        conversation_id=conversation_id,
        message_id=message_id,
        sql=response.sql,
        rows=response.rows,
        analysis=response.analysis,
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


@app.post(
    "/api/dashboards/{dashboard_id}/cards", response_model=DashboardCardDetail
)
async def create_dashboard_card(
    dashboard_id: int, request: CreateDashboardCardRequest
) -> DashboardCardDetail:
    """Pins one card under an existing dashboard -- 404s with zero writes
    if dashboard_id doesn't exist, mirroring post_conversation_message's
    existence-check-then-404 pattern. sql_text/chart_spec_json are stored
    opaquely: no sqlglot validation or execution happens here, only at
    fresh-on-view (a later slice)."""
    async with async_session_factory() as session:
        dashboard = await session.get(Dashboard, dashboard_id)
        if dashboard is None:
            raise HTTPException(status_code=404, detail="dashboard not found")
        card = DashboardCard(
            dashboard_id=dashboard_id,
            title=request.title,
            question_text=request.question_text,
            sql_text=request.sql_text,
            chart_spec_json=request.chart_spec_json,
            position=request.position,
        )
        session.add(card)
        await session.flush()
        result = _card_to_detail(card)
        await session.commit()
    return result


@app.get("/api/dashboards/{dashboard_id}", response_model=DashboardDetail)
async def get_dashboard(dashboard_id: int) -> DashboardDetail:
    """Fresh-on-view -- PRD F6/Sec.8. Re-validates and re-executes every
    pinned card's sql_text on every request rather than serving a cached
    value; the app-schema read (Dashboard/DashboardCard) is closed out
    before any card's SQL is validated/executed, so the app pool never
    overlaps with the two SQL pools _validate_and_execute() uses. Any one
    card failing validation or execution (e.g. schema drift since it was
    pinned) fails the whole request with 502, matching ask()'s
    upstream-pipeline-failure convention, rather than silently dropping
    that card or serving a partial/degraded card list."""
    async with async_session_factory() as session:
        dashboard = await session.get(Dashboard, dashboard_id)
        if dashboard is None:
            raise HTTPException(status_code=404, detail="dashboard not found")
        result = await session.execute(
            select(DashboardCard)
            .where(DashboardCard.dashboard_id == dashboard_id)
            .order_by(DashboardCard.position)
        )
        cards = result.scalars().all()

    card_details = []
    for card in cards:
        try:
            _, rows = await _validate_and_execute(card.sql_text)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        card_details.append(
            DashboardCardWithRows(**_card_to_detail(card).model_dump(), rows=rows)
        )

    return DashboardDetail(
        id=dashboard.id,
        name=dashboard.name,
        created_at=dashboard.created_at,
        cards=card_details,
    )


@app.delete("/api/cards/{card_id}", status_code=204)
async def delete_dashboard_card(card_id: int) -> None:
    """Deletes exactly one pinned card -- PRD Sec.8's
    `DELETE /api/cards/{id}`. Only the DashboardCard row itself is
    removed; the parent Dashboard row is never touched or deleted by
    this route."""
    async with async_session_factory() as session:
        card = await session.get(DashboardCard, card_id)
        if card is None:
            raise HTTPException(status_code=404, detail="card not found")
        await session.delete(card)
        await session.commit()


@app.patch("/api/cards/{card_id}", response_model=DashboardCardDetail)
async def patch_dashboard_card(
    card_id: int, request: PatchDashboardCardRequest
) -> DashboardCardDetail:
    """Renames and/or repositions a pinned card -- PRD Sec.8's
    `PATCH /api/cards/{id} -> rename/position`. Only title/position are
    mutable here; a field omitted (or null) in the request leaves that
    column unchanged, so an empty body is a no-op 200, not a 422.
    sql_text/question_text/chart_spec_json/dashboard_id are never
    touched or re-validated by this route."""
    async with async_session_factory() as session:
        card = await session.get(DashboardCard, card_id)
        if card is None:
            raise HTTPException(status_code=404, detail="card not found")
        if request.title is not None:
            card.title = request.title
        if request.position is not None:
            card.position = request.position
        await session.flush()
        result = _card_to_detail(card)
        await session.commit()
    return result


@app.post("/api/cards/{card_id}/run", response_model=DashboardCardWithRows)
async def run_dashboard_card(card_id: int) -> DashboardCardWithRows:
    """Re-runs exactly one pinned card -- PRD Sec.8's
    `POST /api/cards/{id}/run`. Narrows get_dashboard()'s per-card
    pattern (existence check -> close the app session -> validate/
    execute -> 502 on failure) to a single card: the app-schema read is
    closed out before _validate_and_execute() runs, so the app pool
    never overlaps with the two SQL pools it uses. sql_text itself is
    never mutated -- this is re-execution only, PATCH's job."""
    async with async_session_factory() as session:
        card = await session.get(DashboardCard, card_id)
        if card is None:
            raise HTTPException(status_code=404, detail="card not found")
        card_detail = _card_to_detail(card)

    try:
        _, rows = await _validate_and_execute(card_detail.sql_text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return DashboardCardWithRows(**card_detail.model_dump(), rows=rows)
