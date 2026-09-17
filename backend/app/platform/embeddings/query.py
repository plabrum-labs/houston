"""Similarity-query helper — pgvector cosine distance, RLS-respecting via caller filters."""

from __future__ import annotations

from typing import Any

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.embeddings.deps import get_embedding_client
from app.platform.embeddings.mixin import EmbeddableMixin


async def nearest(
    transaction: AsyncSession,
    model_cls: type[EmbeddableMixin],
    query_text: str,
    *,
    limit: int = 5,
    min_similarity: float | None = None,
    filters: list[ColumnElement[Any]] | None = None,
) -> list[tuple[Any, float]]:
    """Embed `query_text` and return up to `limit` rows ranked by cosine
    similarity. `filters` are ANDed into the WHERE (e.g. RLS scoping, soft-
    delete exclusion). Rows whose embedding is NULL are excluded.

    Cosine similarity = 1 - cosine_distance. `min_similarity` is a lower
    bound on similarity, NOT distance, so a higher value is stricter.
    """
    client = get_embedding_client()
    [vec] = await client.embed([query_text])

    distance = model_cls.embedding.cosine_distance(vec)  # type: ignore[attr-defined]
    similarity = (1 - distance).label("similarity")

    stmt = select(model_cls, similarity).where(model_cls.embedding.is_not(None))
    for f in filters or []:
        stmt = stmt.where(f)
    if min_similarity is not None:
        stmt = stmt.where(distance <= 1 - min_similarity)
    stmt = stmt.order_by(distance).limit(limit)

    result = await transaction.execute(stmt)
    return [(row[0], float(row[1])) for row in result.all()]
