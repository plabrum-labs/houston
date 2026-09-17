"""LLM service — orchestrates thread/message persistence and LLM calls."""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.platform.llm.client import BaseLLMClient
from app.platform.llm.enums import MessageRole
from app.platform.llm.executor import build_tool_executor
from app.platform.llm.models import LLMMessage
from app.platform.llm.prompts import PromptContext, build_system_prompt
from app.platform.llm.queries import (
    create_message,
    create_thread,
    create_tool_call,
    get_messages_by_thread,
    get_thread_by_id,
)
from app.platform.llm.registry import get_tool_definitions
from app.platform.llm.schemas import (
    ErrorEvent,
    MessageCompleteEvent,
    SseEvent,
    SseMessageSchema,
    TokenEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from app.platform.state_machine.roles import Actor
from app.platform.utils.sqids import Sqid

logger = logging.getLogger(__name__)


def _text_prompt(user: Actor[Any] | None, context: dict | None) -> str:
    page = context.get("current_page") if context else None
    persona = config.LLM_PERSONA
    return build_system_prompt("text", PromptContext(user=user, current_page=page), persona=persona)


class LLMService:
    def __init__(self, transaction: AsyncSession, llm_client: BaseLLMClient) -> None:
        self.transaction = transaction
        self.llm_client = llm_client

    def _build_llm_messages(self, history: list[LLMMessage]) -> list[dict]:
        text_keys = {"type", "text"}
        tool_use_keys = {"type", "id", "name", "input"}

        def _clean_block(block: dict) -> dict:
            if block.get("type") == "text":
                return {k: v for k, v in block.items() if k in text_keys}
            if block.get("type") == "tool_use":
                return {k: v for k, v in block.items() if k in tool_use_keys}
            return block

        llm_messages: list[dict] = []
        for msg in history:
            if msg.role == MessageRole.ASSISTANT_TOOL:
                raw = json.loads(msg.content)
                llm_messages.append({"role": "assistant", "content": [_clean_block(b) for b in raw]})
            elif msg.role == MessageRole.TOOL_RESULT:
                llm_messages.append({"role": "user", "content": json.loads(msg.content)})
            else:
                llm_messages.append({"role": msg.role, "content": msg.content})
        return llm_messages

    async def stream_create_thread(
        self,
        content: str,
        user: Actor[Any],
        *,
        context: dict | None = None,
        threadable_type: str | None = None,
        threadable_id: int | None = None,
    ) -> AsyncGenerator[SseEvent]:
        invalidate_keys: list[str] = []
        thread = await create_thread(
            self.transaction,
            user_id=int(user.id),
            threadable_type=threadable_type,
            threadable_id=threadable_id,
            model=self.llm_client.model,
        )
        await create_message(self.transaction, thread_id=thread.id, role=MessageRole.USER, content=content)
        # Explicit commit: the request-scoped transaction has already exited by the time this
        # generator runs (Litestar streams response body after dep cleanup). Without explicit
        # commits, every write here gets rolled back at session teardown.
        await self.transaction.commit()

        executor = build_tool_executor(self.transaction, user, invalidate_keys)
        system = _text_prompt(user, context)
        tools = get_tool_definitions() or None
        full_text = ""
        tool_calls_this_turn: list[dict] = []

        async def persist_tool_message(role: MessageRole, json_content: str) -> None:
            await create_message(self.transaction, thread_id=thread.id, role=role, content=json_content)
            await self.transaction.commit()

        try:
            async for ev in self.llm_client.stream(
                [{"role": "user", "content": content}],
                system=system,
                tools=tools,
                tool_executor=executor,
                persist_tool_message=persist_tool_message,
            ):
                yield ev
                if isinstance(ev, TokenEvent):
                    full_text += ev.delta
                elif isinstance(ev, ToolCallEvent):
                    tool_calls_this_turn.append({"id": ev.id, "name": ev.name, "input": ev.input, "is_error": False})
                elif isinstance(ev, ToolResultEvent):
                    for tc in tool_calls_this_turn:
                        if tc["id"] == ev.tool_use_id:
                            tc["is_error"] = ev.is_error

            assistant_msg = await create_message(
                self.transaction, thread_id=thread.id, role=MessageRole.ASSISTANT, content=full_text
            )
            for tc in tool_calls_this_turn:
                await create_tool_call(
                    self.transaction,
                    message_id=int(assistant_msg.id),
                    tool_use_id=tc["id"],
                    name=tc["name"],
                    input=tc["input"],
                    is_error=tc["is_error"],
                )
            await self.transaction.commit()
            yield MessageCompleteEvent(
                thread_id=str(Sqid(thread.id)),
                message=SseMessageSchema(
                    id=str(assistant_msg.id),
                    thread_id=str(Sqid(assistant_msg.thread_id)),
                    role=assistant_msg.role,
                    content=assistant_msg.content,
                    created_at=assistant_msg.created_at.isoformat(),
                ),
                invalidate_queries=invalidate_keys,
            )
        except Exception:
            logger.exception("LLM stream failed for thread %s", thread.id)
            yield ErrorEvent(message="The assistant encountered an error. Your message was saved.")

    async def stream_send_message(
        self,
        thread_id: int,
        content: str,
        user: Actor[Any],
        *,
        context: dict | None = None,
    ) -> AsyncGenerator[SseEvent]:
        thread = await get_thread_by_id(self.transaction, thread_id)
        if thread is None:
            logger.warning("stream_send_message called with unknown thread_id=%s", thread_id)
            yield ErrorEvent(message="Thread not found.", code="thread_not_found")
            return

        await create_message(self.transaction, thread_id=thread.id, role=MessageRole.USER, content=content)
        await self.transaction.commit()

        history = await get_messages_by_thread(self.transaction, thread_id)
        llm_messages = self._build_llm_messages(history)

        invalidate_keys: list[str] = []
        executor = build_tool_executor(self.transaction, user, invalidate_keys)
        system = _text_prompt(user, context)
        tools = get_tool_definitions() or None
        full_text = ""
        tool_calls_this_turn: list[dict] = []

        async def persist_tool_message(role: MessageRole, json_content: str) -> None:
            await create_message(self.transaction, thread_id=thread_id, role=role, content=json_content)
            await self.transaction.commit()

        try:
            async for ev in self.llm_client.stream(
                llm_messages,
                system=system,
                tools=tools,
                tool_executor=executor,
                persist_tool_message=persist_tool_message,
            ):
                yield ev
                if isinstance(ev, TokenEvent):
                    full_text += ev.delta
                elif isinstance(ev, ToolCallEvent):
                    tool_calls_this_turn.append({"id": ev.id, "name": ev.name, "input": ev.input, "is_error": False})
                elif isinstance(ev, ToolResultEvent):
                    for tc in tool_calls_this_turn:
                        if tc["id"] == ev.tool_use_id:
                            tc["is_error"] = ev.is_error

            assistant_msg = await create_message(
                self.transaction, thread_id=thread_id, role=MessageRole.ASSISTANT, content=full_text
            )
            for tc in tool_calls_this_turn:
                await create_tool_call(
                    self.transaction,
                    message_id=int(assistant_msg.id),
                    tool_use_id=tc["id"],
                    name=tc["name"],
                    input=tc["input"],
                    is_error=tc["is_error"],
                )
            await self.transaction.commit()
            yield MessageCompleteEvent(
                thread_id=str(Sqid(thread.id)),
                message=SseMessageSchema(
                    id=str(assistant_msg.id),
                    thread_id=str(Sqid(assistant_msg.thread_id)),
                    role=assistant_msg.role,
                    content=assistant_msg.content,
                    created_at=assistant_msg.created_at.isoformat(),
                ),
                invalidate_queries=invalidate_keys,
            )
        except Exception:
            logger.exception("LLM stream failed for thread %s", thread_id)
            yield ErrorEvent(message="The assistant encountered an error. Your message was saved.")
