"""Tool registry for the agentic loop.

Domain tools use @register_tool and subclass SloopTool.
Importing a module that calls @register_tool is sufficient to register tools —
factory.py's discover_and_import(["tools.py"]) handles this automatically.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar

from msgspec import Struct
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.llm.schemas import InputSchema, ToolDefinition
from app.platform.state_machine.roles import Actor
from app.platform.utils.sqids import Sqid

logger = logging.getLogger(__name__)

_TOOL_REGISTRY: dict[str, type["SloopTool"]] = {}


@dataclass
class ToolContext:
    db: AsyncSession
    user: Actor[Any]
    invalidate_keys: list[str] = field(default_factory=list)


@dataclass
class ToolResult:
    data: Any = None
    message: str = ""


class SloopTool(ABC):
    name: ClassVar[str]
    description: ClassVar[str]
    input_schema: ClassVar[InputSchema]
    input_struct: ClassVar[type[Struct]]
    # The app supplies its own Role enum (Actor.role); the platform names no role values.
    allowed_roles: ClassVar[frozenset[Enum]] = frozenset()

    @abstractmethod
    async def execute(self, ctx: ToolContext, args: Any) -> "ToolResult | str": ...

    @classmethod
    def definition(cls) -> ToolDefinition:
        return ToolDefinition(name=cls.name, description=cls.description, input_schema=cls.input_schema)


def register_tool(cls: type[SloopTool]) -> type[SloopTool]:
    """Decorator: validate ClassVars then register in _TOOL_REGISTRY."""
    for attr in ("name", "description", "input_schema", "input_struct"):
        if not hasattr(cls, attr):
            raise TypeError(f"{cls.__name__} is missing required ClassVar: {attr!r}")
    if cls.name in _TOOL_REGISTRY:
        logger.warning("Tool %r already registered — overwriting", cls.name)
    _TOOL_REGISTRY[cls.name] = cls
    return cls


def get_tool_class(name: str) -> type[SloopTool] | None:
    return _TOOL_REGISTRY.get(name)


def get_tool_definitions() -> list[ToolDefinition]:
    return [cls.definition() for cls in _TOOL_REGISTRY.values()]


def _json_default(obj: object) -> object:
    if isinstance(obj, Sqid):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    raise TypeError(f"Not JSON serializable: {type(obj)!r}")


def serialize_tool_result(result: "ToolResult | str") -> str:
    if isinstance(result, str):
        return result
    parts: dict[str, Any] = {}
    if result.data is not None:
        parts["data"] = result.data
    if result.message:
        parts["message"] = result.message
    return json.dumps(parts, default=_json_default)
