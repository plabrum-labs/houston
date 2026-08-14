"""Global cross-entity search router over the `SearchRegistry`.

The source app mounts a module-level `search_router` guarded by `requires_session`
and injects the concrete `User` to apply an org-scope WHERE clause. The platform owns
neither, so this is a factory: the app injects its guards, and row
scoping is left to RLS — the per-model org/user policy filters the search
just as it filters CRUD, so the handler needs no principal at all.
"""

from __future__ import annotations

from collections.abc import Sequence

import msgspec
from litestar import Router, get
from litestar.params import Dependency, Parameter
from litestar.types import Guard
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.base.search import SearchRegistry
from app.platform.utils.sqids import Sqid


class SearchResult(msgspec.Struct):
    entity_type: str
    id: Sqid
    label: str
    sublabel: str | None
    path: str


class SearchResponse(msgspec.Struct):
    results: list[SearchResult]
    query: str
    entity_filter: str | None


def _sublabel(row: object, model_cls: type, term: str) -> str | None:
    term_lower = term.lower()
    for col_name in model_cls.trgm_columns:
        if col_name == model_cls.search_label_field:
            continue
        val = getattr(row, col_name, None)
        if val and term_lower in val.lower():
            return val
    return None


def build_search_router(*, path: str = "/", guards: Sequence[Guard] = ()) -> Router:
    """Build the global-search router for an app.

    Args:
        path: Mount path (default "/").
        guards: Litestar guards applied to the search route (e.g. requires_session).
    """

    @get("/search", guards=list(guards), tags=["search"])
    async def search(
        q: str = Parameter(query="q", default=""),
        limit: int = Parameter(query="limit", default=5, ge=1, le=50),
        transaction: AsyncSession = Dependency(skip_validation=True),
    ) -> SearchResponse:
        # Parse optional entity_type: prefix
        entity_filter: str | None = None
        term = q.strip()
        if ":" in term:
            prefix, rest = term.split(":", 1)
            prefix = prefix.strip()
            if prefix in SearchRegistry:
                entity_filter = prefix
                term = rest.strip()

        models_to_search = {
            key: cls
            for key, cls in SearchRegistry.items()
            if (entity_filter is None and cls.search_global) or entity_filter == key
        }

        results: list[SearchResult] = []

        for entity_type, model_cls in models_to_search.items():
            if not term:
                continue

            # No org-scope WHERE clause — RLS scopes each model's rows.
            search_clause = model_cls.search_filter(term)
            if search_clause is None:
                continue

            stmt = select(model_cls).where(search_clause).limit(limit)
            rows = (await transaction.execute(stmt)).scalars().all()

            for row in rows:
                results.append(
                    SearchResult(
                        entity_type=entity_type,
                        id=row.id,
                        label=row.get_search_label(),
                        sublabel=_sublabel(row, model_cls, term),
                        path=f"{model_cls.search_detail_prefix}/{row.id}",
                    )
                )

        return SearchResponse(
            results=results,
            query=term,
            entity_filter=entity_filter,
        )

    return Router(path=path, route_handlers=[search], tags=["search"])
