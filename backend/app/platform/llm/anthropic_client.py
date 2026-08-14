"""Live Anthropic LLM client — the only module in `llm` that needs `anthropic`
installed. Import this directly (not via `llm/__init__.py`) when you want the
real client; `llm/deps.py` selects it lazily inside its provider getters so a
`Local*`-only app never needs the SDK.
"""

import json
import logging
from collections.abc import AsyncGenerator

import anthropic
import msgspec

from app.config import config
from app.platform.llm.client import BaseLLMClient
from app.platform.llm.enums import MessageRole
from app.platform.llm.executor import PersistToolMessageFn, ToolExecutorFn
from app.platform.llm.schemas import ErrorEvent, SseEvent, TokenEvent, ToolCallEvent, ToolDefinition, ToolResultEvent

logger = logging.getLogger(__name__)


class AnthropicLLMClient(BaseLLMClient):
    MODEL = "claude-sonnet-4-6"

    def __init__(self, api_key: str | None = None) -> None:
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key or config.ANTHROPIC_API_KEY,
            timeout=anthropic.Timeout(connect=10.0, read=120.0, write=10.0, pool=5.0),
        )

    @property
    def model(self) -> str:
        return self.MODEL

    async def chat(
        self,
        messages: list[dict],
        *,
        system: str | None = None,
        tools: list[ToolDefinition] | None = None,
        tool_executor: ToolExecutorFn | None = None,
        persist_tool_message: PersistToolMessageFn | None = None,
    ) -> str:
        text_parts: list[str] = []
        async for ev in self.stream(
            messages,
            system=system,
            tools=tools,
            tool_executor=tool_executor,
            persist_tool_message=persist_tool_message,
        ):
            if isinstance(ev, TokenEvent):
                text_parts.append(ev.delta)
            elif isinstance(ev, ErrorEvent):
                return ev.message
        return "".join(text_parts)

    async def stream(  # type: ignore[override]
        self,
        messages: list[dict],
        *,
        system: str | None = None,
        tools: list[ToolDefinition] | None = None,
        tool_executor: ToolExecutorFn | None = None,
        persist_tool_message: PersistToolMessageFn | None = None,
    ) -> AsyncGenerator[SseEvent]:
        msgs = list(messages)
        max_iterations = 10

        for _ in range(max_iterations):
            kwargs: dict = {
                "model": self.MODEL,
                "max_tokens": 8096,
                "messages": msgs,
            }
            if system:
                # Tag system block for prompt caching
                kwargs["system"] = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
            if tools:
                tool_defs = msgspec.to_builtins(tools)
                # Tag last tool definition for prompt caching
                if tool_defs:
                    tool_defs[-1] = {**tool_defs[-1], "cache_control": {"type": "ephemeral"}}
                kwargs["tools"] = tool_defs

            try:
                async with self._client.messages.stream(**kwargs) as stream_ctx:
                    async for text in stream_ctx.text_stream:
                        yield TokenEvent(delta=text)
                    final = await stream_ctx.get_final_message()
            except anthropic.APIError as exc:
                logger.exception("Anthropic API error during stream")
                yield ErrorEvent(message=str(exc))
                return

            if final.stop_reason == "tool_use" and tool_executor is not None:
                assistant_content = [block.model_dump() for block in final.content]
                msgs.append({"role": "assistant", "content": final.content})

                if persist_tool_message is not None:
                    await persist_tool_message(MessageRole.ASSISTANT_TOOL, json.dumps(assistant_content))

                tool_results = []
                for block in final.content:
                    if block.type == "tool_use":
                        yield ToolCallEvent(id=block.id, name=block.name, input=block.input)
                        result, is_error = await tool_executor(block.name, block.input)
                        yield ToolResultEvent(tool_use_id=block.id, is_error=is_error)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            }
                        )

                msgs.append({"role": "user", "content": tool_results})

                if persist_tool_message is not None:
                    await persist_tool_message(MessageRole.TOOL_RESULT, json.dumps(tool_results))

                continue

            return

        logger.warning("LLM streaming loop hit max_iterations=%d", max_iterations)
        yield ErrorEvent(message="Request could not be completed.")
