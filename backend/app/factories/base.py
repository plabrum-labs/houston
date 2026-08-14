"""Base polyfactory for all houston models — generic over `BaseDBModel`.

Faker-backed field generation, async create helpers that flush+refresh, pgvector as a
plain list, PK left to the DB sequence, and GENERATED columns (`SearchMixin`'s
`search_trgm`/`search_vector`) dropped so they're not force-inserted. Per-model
factories subclass this and set `__model__`.
"""

from typing import Any

from faker import Faker
from pgvector.sqlalchemy import Vector
from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.base.models import BaseDBModel


class BaseFactory[T: BaseDBModel](SQLAlchemyFactory[T]):
    __is_base_factory__ = True
    __faker__ = Faker()
    __session__ = None
    __check_model__ = False
    __set_relationships__ = False
    __set_association_proxy__ = False
    __set_primary_key__ = False  # let PostgreSQL sequences assign IDs

    deleted_at = None
    # pgvector embeddings are populated by the embed task, not by factories.
    embedding = None

    @classmethod
    def get_sqlalchemy_types(cls) -> dict[Any, Any]:
        types = dict(super().get_sqlalchemy_types())
        types[Vector] = list
        return types

    @classmethod
    def build(cls, **kwargs: Any) -> Any:
        """Build an instance, then unset any GENERATED columns the factory populated.

        `SearchMixin` maps `search_trgm`/`search_vector` as Postgres GENERATED columns;
        polyfactory fills every mapped column, so they must be removed or the INSERT
        fails ("cannot insert a non-DEFAULT value into a generated column"). Deleting
        the attribute (vs setting None) leaves it unset so SQLAlchemy omits it.
        """
        instance = super().build(**kwargs)
        mapper = sa_inspect(cls.__model__)
        for column in cls.__model__.__table__.columns:
            if column.computed is None:
                continue
            key = mapper.get_property_by_column(column).key
            if key not in kwargs:
                try:
                    delattr(instance, key)
                except AttributeError:
                    pass
        return instance

    @classmethod
    async def create_async(cls, session: AsyncSession, **kwargs: Any) -> T:  # type: ignore[override]
        instance = cls.build(**kwargs)
        session.add(instance)
        await session.flush()
        await session.refresh(instance)
        return instance

    @classmethod
    async def create_batch_async(cls, session: AsyncSession, size: int, **kwargs: Any) -> list[T]:  # type: ignore[override]
        instances = [cls.build(**kwargs) for _ in range(size)]
        for instance in instances:
            session.add(instance)
        await session.flush()
        for instance in instances:
            await session.refresh(instance)
        return instances
