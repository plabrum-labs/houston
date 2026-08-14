"""Build a per-request tool executor closure for the LLM agent loop."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

import msgspec
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.llm.enums import MessageRole
from app.platform.llm.registry import ToolContext, get_tool_class, serialize_tool_result
from app.platform.state_machine.roles import Actor
from app.platform.utils.sqids import sqid_dec_hook

logger = logging.getLogger(__name__)

ToolExecutorFn = Callable[[str, dict], Awaitable[tuple[str, bool]]]
PersistToolMessageFn = Callable[[MessageRole, str], Awaitable[None]]


def build_tool_executor(
    db: AsyncSession,
    user: Actor[Any],
    invalidate_keys: list[str],
) -> ToolExecutorFn:
    async def execute(name: str, inputs: dict) -> tuple[str, bool]:
        tool_cls = get_tool_class(name)
        if tool_cls is None:
            return f"Unknown tool: {name}", True
        if tool_cls.allowed_roles and user.role not in tool_cls.allowed_roles:
            logger.warning("Role %r denied tool %r", user.role, name)
            return "That tool is not available for your role.", True
        try:
            args = msgspec.convert(inputs, tool_cls.input_struct, dec_hook=sqid_dec_hook)
        except msgspec.ValidationError:
            logger.warning("Tool input invalid for %r: %r", name, inputs)
            return "Tool input invalid.", True
        ctx = ToolContext(db=db, user=user, invalidate_keys=invalidate_keys)
        try:
            result = await tool_cls().execute(ctx, args)
        except Exception:
            logger.warning("Tool %r raised an exception", name, exc_info=True)
            return f"Tool {name!r} encountered an error. Let the user know and try a different approach.", True
        return serialize_tool_result(result), False

    return execute
