"""`BaseExtractor` — typed extractor base class.

Extractors are stateless: every entry point is a classmethod, and callers
invoke them on the class (`MyExtractor.run(...)`) without instantiating.
Per-call context (e.g. source-message provenance) flows as kwargs or is
stamped on the returned model by the caller — never stashed on an instance.

Prompts are a per-call concern, not a per-extractor property. Field-level
guidance lives on the msgspec schemas as `Annotated[T, Meta(description=...)]`
and propagates to the LLM via the tool's `input_schema`. The `extract()`
caller passes a task-framing prompt; a schema-derived default covers
standalone / test calls.

`Document` and `ExtractionError` live in `.types`; both this module and
`llm.extract` import them from there to break the import cycle.
"""

from __future__ import annotations

from msgspec import Struct
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.base.models import BaseDBModel
from app.platform.extraction.types import Document
from app.platform.llm.extract import llm_extract


def _default_prompt(schema: type[Struct]) -> str:
    return (
        f"Extract a {schema.__name__} from the document. "
        f"Fill every required field; leave optional fields null if the document doesn't state them. "
        f"Use the document literally — do not invent values."
    )


class BaseExtractor[TSchema: Struct, TModel: BaseDBModel]:
    """Typed extractor — one LLM-extracted schema, one domain model.

    Subclasses set `schema` and `model`, override `create` (always) and
    `lookup` (when there's a sensible dedupe key), and compose child
    extractors inside `create` via attribute access on the parsed schema.

    Two entry points:
      - `extract(document, prompt=...)`: top-level. Runs the LLM, then
        `run(parsed)`. The caller passes a task-framing prompt; if omitted,
        a schema-derived default is used.
      - `run(data)`: skips the LLM. Called by parent extractors against
        already-parsed child schemas and by tests/admin tools with hand-built
        data.
    """

    schema: type[TSchema]
    model: type[TModel]

    @classmethod
    async def extract(
        cls,
        transaction: AsyncSession,
        document: Document,
        *,
        prompt: str | None = None,
    ) -> TModel:
        parsed = await llm_extract(
            document,
            schema=cls.schema,
            prompt=prompt or _default_prompt(cls.schema),
        )
        return await cls.run(transaction, parsed)

    @classmethod
    async def run(cls, transaction: AsyncSession, data: TSchema) -> TModel:
        existing = await cls.lookup(transaction, data)
        if existing is not None:
            return existing
        return await cls.create(transaction, data)

    @classmethod
    async def lookup(cls, transaction: AsyncSession, data: TSchema) -> TModel | None:
        return None

    @classmethod
    async def create(cls, transaction: AsyncSession, data: TSchema) -> TModel:
        raise NotImplementedError(f"{cls.__name__} must override create()")
