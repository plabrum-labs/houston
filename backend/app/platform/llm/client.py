"""LLM client abstraction + local dev stub.

The real provider implementations live in their own modules —
`app.platform.llm.anthropic_client` (`AnthropicLLMClient`) and `app.platform.llm.openai_client`
(`OpenAILLMClient`) — so importing `BaseLLMClient`/`LocalLLMClient` (all a
`Local*`-only app needs) never requires `anthropic`/`openai` to be installed.
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from litestar import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.llm.executor import PersistToolMessageFn, ToolExecutorFn
from app.platform.llm.schemas import SseEvent, TokenEvent, ToolDefinition
from app.platform.state_machine.roles import Actor

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """Provider-agnostic LLM client interface.

    Each modality (text chat / streaming / realtime voice) is a separate
    optional capability. Subclasses implement what their provider supports;
    callers should not need to know which provider is in use, and provider
    selection lives entirely in `deps.py`.
    """

    @property
    @abstractmethod
    def model(self) -> str: ...

    @property
    def embedding_model(self) -> str:
        raise NotImplementedError(f"{type(self).__name__} does not support embeddings")

    @property
    def embedding_dim(self) -> int:
        raise NotImplementedError(f"{type(self).__name__} does not support embeddings")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError(f"{type(self).__name__} does not support embeddings")

    async def chat(
        self,
        messages: list[dict],
        *,
        system: str | None = None,
        tools: list[ToolDefinition] | None = None,
        tool_executor: ToolExecutorFn | None = None,
        persist_tool_message: PersistToolMessageFn | None = None,
    ) -> str:
        raise NotImplementedError(f"{type(self).__name__} does not support text chat")

    async def stream(
        self,
        messages: list[dict],
        *,
        system: str | None = None,
        tools: list[ToolDefinition] | None = None,
        tool_executor: ToolExecutorFn | None = None,
        persist_tool_message: PersistToolMessageFn | None = None,
    ) -> AsyncGenerator[SseEvent]:
        raise NotImplementedError(f"{type(self).__name__} does not support text streaming")
        yield  # pragma: no cover

    async def voice_stream(
        self,
        socket: WebSocket,
        *,
        db_session: AsyncSession,
        user: Actor[Any],
        thread_id: int,
        system_prompt: str,
    ) -> None:
        raise NotImplementedError(f"{type(self).__name__} does not support voice")


class LocalLLMClient(BaseLLMClient):
    @property
    def model(self) -> str:
        return "local-dev"

    async def chat(
        self,
        messages: list[dict],
        *,
        system: str | None = None,
        tools: list[ToolDefinition] | None = None,
        tool_executor: ToolExecutorFn | None = None,
        persist_tool_message: PersistToolMessageFn | None = None,
    ) -> str:
        logger.info("[dev] LLM chat called — returning stub response")
        return "[dev mode: LLM disabled]"

    async def stream(  # type: ignore[override]
        self,
        messages: list[dict],
        *,
        system: str | None = None,
        tools: list[ToolDefinition] | None = None,
        tool_executor: ToolExecutorFn | None = None,
        persist_tool_message: PersistToolMessageFn | None = None,
    ) -> AsyncGenerator[SseEvent]:
        logger.info("[dev] LLM stream called — returning stub response")
        yield TokenEvent(delta="[dev mode: LLM disabled]")
