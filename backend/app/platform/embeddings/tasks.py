"""Embedding tasks: per-row embed + sweeper backstop."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.base.models import BaseDBModel
from app.platform.embeddings.deps import get_embedding_client
from app.platform.embeddings.enums import EmbeddingTaskName
from app.platform.embeddings.hash import sha256_bytes
from app.platform.embeddings.mixin import EmbeddableMixin
from app.platform.queue.registry import task
from app.platform.queue.transactions import with_transaction
from app.platform.queue.types import PlatformContext

logger = logging.getLogger(__name__)


def _embeddable_classes() -> list[type[EmbeddableMixin]]:
    return [m for m in BaseDBModel.get_all_models() if issubclass(m, EmbeddableMixin) and m.embedding_columns]


def _class_for_table(table: str) -> type[EmbeddableMixin] | None:
    for cls in _embeddable_classes():
        if cls.__tablename__ == table:
            return cls
    return None


@task(EmbeddingTaskName.EMBED_ROW)
@with_transaction
async def embed_row_task(ctx: PlatformContext, *, transaction: AsyncSession, table: str, id: int) -> dict[str, Any]:
    """Embed one row. Idempotent: skips the API call when content hash + model
    still match the stored values, but bumps embedded_at for observability."""
    cls = _class_for_table(table)
    if cls is None:
        logger.warning(f"embed_row_task: no embeddable class for table={table!r}")
        return {"status": "no_class", "table": table, "id": id}

    row = await transaction.scalar(select(cls).where(cls.id == id))
    if row is None:
        return {"status": "missing", "table": table, "id": id}

    content = row.embedding_content()
    content_hash = sha256_bytes(content)
    target_model = cls.embedding_model

    if row.embedding_content_hash == content_hash and row.embedded_model == target_model and row.embedding is not None:
        row.embedded_at = datetime.now(tz=UTC)
        return {"status": "fresh", "table": table, "id": id}

    client = get_embedding_client()
    if client.dim != cls.embedding_dim:
        logger.error(f"embed_row_task: dim mismatch for {table}: client.dim={client.dim} class.dim={cls.embedding_dim}")
        return {"status": "dim_mismatch", "table": table, "id": id}

    [vector] = await client.embed([content])
    row.embedding = vector
    row.embedding_content_hash = content_hash
    row.embedded_model = target_model
    row.embedded_at = datetime.now(tz=UTC)
    return {"status": "embedded", "table": table, "id": id}


@task(EmbeddingTaskName.SWEEP_EMBEDDINGS)
@with_transaction
async def sweep_embeddings_task(
    ctx: PlatformContext, *, transaction: AsyncSession, limit_per_model: int = 500
) -> dict[str, Any]:
    """Find stale/missing embeddings on classes with sweep_enabled=True and
    enqueue per-row embeds. Off by default; flip on for model upgrades or
    after worker outages."""
    queue = ctx.get("queue")
    counts: dict[str, int] = {}
    for cls in _embeddable_classes():
        if not cls.sweep_enabled:
            continue
        stmt = (
            select(cls.id)
            .where(
                (cls.embedding.is_(None))
                | (cls.embedding_content_hash.is_(None))
                | (cls.embedded_model != cls.embedding_model)
            )
            .limit(limit_per_model)
        )
        rows = (await transaction.execute(stmt)).scalars().all()
        counts[cls.__tablename__] = len(rows)
        if queue is None:
            continue
        for row_id in rows:
            await queue.enqueue(str(EmbeddingTaskName.EMBED_ROW), table=cls.__tablename__, id=int(row_id))
    return {"status": "swept", "counts": counts}
