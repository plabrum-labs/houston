"""LLM chat routes — SSE streaming, thread/message CRUD, and realtime voice WS."""

from collections.abc import AsyncGenerator, Sequence
from typing import Any

from litestar import Router, WebSocket, delete, get, post, websocket
from litestar.params import Dependency
from litestar.response import Stream
from litestar.types import Guard
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.platform.llm.client import BaseLLMClient
from app.platform.llm.prompts import PromptContext, build_system_prompt
from app.platform.llm.queries import create_thread, delete_thread, get_messages_after, list_threads_by_user
from app.platform.llm.schemas import (
    CreateThreadBody,
    MessagePageSchema,
    MessageSchema,
    SendMessageBody,
    ThreadListPage,
    ThreadSummarySchema,
    ToolCallRecord,
)
from app.platform.llm.service import LLMService
from app.platform.state_machine.roles import Actor
from app.platform.streaming.sse import format_frame, stream_response
from app.platform.streaming.ws import run_websocket
from app.platform.utils.deps import rls_transaction
from app.platform.utils.sqids import Sqid


@get("/threads")
async def list_threads_handler(
    transaction: AsyncSession,
    user: Actor[Any] = Dependency(skip_validation=True),
) -> ThreadListPage:
    rows = await list_threads_by_user(transaction, user.id)
    summaries = [
        ThreadSummarySchema(
            id=thread.id,
            title=(first_content[:80] if first_content else None),
            last_message_at=last_at,
        )
        for thread, first_content, last_at in rows
    ]
    return ThreadListPage(threads=summaries)


@get("/threads/{thread_id:str}/messages")
async def get_thread_messages_handler(
    thread_id: Sqid,
    transaction: AsyncSession,
    after: Sqid | None = None,
    limit: int = 50,
) -> MessagePageSchema:
    messages, has_more = await get_messages_after(transaction, thread_id, after_id=after, limit=limit)
    return MessagePageSchema(
        messages=[
            MessageSchema(
                id=msg.id,
                thread_id=Sqid(msg.thread_id),
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
                tool_calls=[
                    ToolCallRecord(id=tc.tool_use_id, name=tc.name, input=tc.input, is_error=tc.is_error)
                    for tc in msg.tool_calls
                ],
            )
            for msg in messages
        ],
        has_more=has_more,
        next_cursor=Sqid(messages[-1].id) if has_more and messages else None,
    )


@delete("/threads/{thread_id:str}", status_code=204)
async def delete_thread_handler(
    thread_id: Sqid,
    transaction: AsyncSession,
) -> None:
    await delete_thread(transaction, thread_id)


@post("/threads/stream")
async def stream_create_thread_handler(
    data: CreateThreadBody,
    llm_service: LLMService,
    user: Actor[Any] = Dependency(skip_validation=True),
) -> Stream:
    async def gen() -> AsyncGenerator[bytes]:
        async for ev in llm_service.stream_create_thread(
            data.content,
            user=user,
            context=data.context,
            threadable_type=data.threadable_type,
            threadable_id=data.threadable_id,
        ):
            yield format_frame(ev)

    return stream_response(gen())


@post("/threads/{thread_id:str}/messages/stream")
async def stream_send_message_handler(
    thread_id: Sqid,
    data: SendMessageBody,
    llm_service: LLMService,
    user: Actor[Any] = Dependency(skip_validation=True),
) -> Stream:
    async def gen() -> AsyncGenerator[bytes]:
        async for ev in llm_service.stream_send_message(
            thread_id,
            data.content,
            user=user,
            context=data.context,
        ):
            yield format_frame(ev)

    return stream_response(gen())


@websocket("/voice")
async def voice_handler(
    socket: WebSocket,
    db_session: AsyncSession,
    voice_llm_client: BaseLLMClient,
) -> None:
    async def handle(ws: WebSocket, user: Actor[Any]) -> None:
        async with rls_transaction(db_session, user_id=user.id, organization_id=user.organization_id) as txn:
            thread = await create_thread(txn, user_id=user.id, model=voice_llm_client.model)

        await voice_llm_client.voice_stream(
            ws,
            db_session=db_session,
            user=user,
            thread_id=thread.id,
            system_prompt=build_system_prompt("voice", PromptContext(user=user), persona=config.LLM_PERSONA),
        )

    await run_websocket(socket, label="Voice WS", handler=handle)


def build_llm_router(*, path: str = "/llm", guards: Sequence[Guard] = ()) -> Router:
    return Router(
        path=path,
        route_handlers=[
            list_threads_handler,
            get_thread_messages_handler,
            delete_thread_handler,
            stream_create_thread_handler,
            stream_send_message_handler,
            voice_handler,
        ],
        guards=list(guards),
        tags=["llm"],
    )
