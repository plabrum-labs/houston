from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy import event
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.platform.base.models import BaseDBModel
from app.platform.embeddings.events import stage_embed_after_insert, stage_embed_after_update
from app.platform.embeddings.hash import sha256_bytes


class EmbeddableMixin(BaseDBModel):
    """Adds a pgvector embedding + freshness metadata to a model.

    Subclasses declare:
      - `embedding_columns: ClassVar[list[str]]` — columns whose concatenated
        text is hashed and embedded. Mirrors the SearchMixin shape.
      - `embedding_dim: ClassVar[int]` — must match the configured model's dim.
      - Optionally override `embedding_content()` for non-trivial content.
    """

    __abstract__ = True

    embedding_columns: ClassVar[list[str]] = []
    embedding_dim: ClassVar[int] = 1536
    embedding_model: ClassVar[str] = "text-embedding-3-small"
    sweep_enabled: ClassVar[bool] = False

    @declared_attr
    def embedding(self) -> Mapped[Any | None]:
        return mapped_column(Vector(self.embedding_dim), nullable=True)

    embedded_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    embedded_model: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    embedding_content_hash: Mapped[bytes | None] = mapped_column(sa.LargeBinary(32), nullable=True)

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if not cls.embedding_columns and "embedding_content" not in cls.__dict__:
            return
        event.listen(cls, "after_insert", stage_embed_after_insert, propagate=False)
        event.listen(cls, "after_update", stage_embed_after_update, propagate=False)

    def embedding_content(self) -> str:
        return "\n".join(str(getattr(self, c, "") or "") for c in type(self).embedding_columns)

    def is_embedding_stale(self) -> bool:
        if self.embedding is None or self.embedding_content_hash is None:
            return True
        if self.embedded_model != type(self).embedding_model:
            return True
        return sha256_bytes(self.embedding_content()) != self.embedding_content_hash
