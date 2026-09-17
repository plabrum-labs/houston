from __future__ import annotations

from typing import Any, ClassVar

import sqlalchemy as sa
from sqlalchemy import ColumnElement, Index, or_
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import declared_attr

from app.platform.base.models import BaseDBModel

# Keyed by search_entity_type → model class
SearchRegistry: dict[str, type[SearchMixin]] = {}


class SearchMixin(BaseDBModel):
    """Abstract mixin — never mapped directly; concrete subclasses get trgm/fts columns."""

    __abstract__ = True

    trgm_columns: ClassVar[list[str]] = []  # pg_trgm ilike — names, codes, proper nouns
    fts_columns: ClassVar[list[str]] = []  # english FTS — prose, notes, summaries

    search_global: ClassVar[bool] = True
    search_label_field: ClassVar[str]
    search_entity_type: ClassVar[str]
    search_detail_prefix: ClassVar[str]

    # Set by __init_subclass__ on subclasses that declare trgm_columns / fts_columns.
    # Typed as Any so search_filter can call .ilike() / .op() without narrowing.
    search_trgm: ClassVar[Any]
    search_vector: ClassVar[Any]

    def __init_subclass__(cls, **kwargs: object) -> None:
        # Register the computed columns BEFORE super() triggers SQLAlchemy mapping;
        # assigning a declared_attr after the mapper has already scanned the class
        # silently drops the column (same class of fix as UserMixin / StateMachineMixin).
        if cls.trgm_columns:
            trgm_expr = " || ' ' || ".join(f"coalesce({c}, '')" for c in cls.trgm_columns)

            @declared_attr
            def search_trgm(c: Any) -> sa.Column[str]:
                return sa.Column(sa.Text, sa.Computed(trgm_expr, persisted=True), nullable=True)

            cls.search_trgm = search_trgm

        if cls.fts_columns:
            fts_expr = " || ' ' || ".join(f"coalesce({c}, '')" for c in cls.fts_columns)

            @declared_attr
            def search_vector(c: Any) -> sa.Column[Any]:
                return sa.Column(
                    TSVECTOR,
                    sa.Computed(f"to_tsvector('english', {fts_expr})", persisted=True),
                    nullable=True,
                )

            cls.search_vector = search_vector

        super().__init_subclass__(**kwargs)

    @classmethod
    def __declare_last__(cls) -> None:
        if cls.trgm_columns and "search_trgm" in cls.__table__.c:
            Index(
                f"ix_{cls.__tablename__}_trgm",
                cls.__table__.c.search_trgm,
                postgresql_using="gin",
                postgresql_ops={"search_trgm": "gin_trgm_ops"},
            )
        if cls.fts_columns and "search_vector" in cls.__table__.c:
            Index(
                f"ix_{cls.__tablename__}_search_vector",
                cls.__table__.c.search_vector,
                postgresql_using="gin",
            )

    @classmethod
    def search_filter(cls, term: str) -> ColumnElement | None:
        if not term or not term.strip():
            return None
        conditions = []
        if cls.trgm_columns and "search_trgm" in cls.__table__.c:
            conditions.append(cls.__table__.c["search_trgm"].ilike(f"%{term}%"))
        if cls.fts_columns and "search_vector" in cls.__table__.c:
            conditions.append(cls.__table__.c["search_vector"].op("@@")(sa.func.websearch_to_tsquery("english", term)))
        return or_(*conditions) if conditions else None

    def get_search_label(self) -> str:
        return str(getattr(self, self.__class__.search_label_field, "") or "")
