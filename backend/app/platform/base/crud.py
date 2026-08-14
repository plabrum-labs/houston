"""CRUD read pillar: declarative list/detail endpoints generated from a config.

The platform doesn't own the app's concrete `User` or its auth guards, so two things
are decoupled from the source app's version:
  - the principal is the `Actor` protocol (D2); the concrete `User` is injected by
    the app and passed through to the transformer callables — the platform never reads
    an attribute off it,
  - the base guard (`requires_session` in the source app) is injected via `base_guards`
    (same seam as `build_action_router`, D15).

Row scoping is **entirely RLS's job** (D18): the request transaction sets
`app.organization_id` / `app.user_id`, and each model's `OrgScopedMixin` /
`UserScopedMixin` policy filters rows in Postgres. The source app re-applies a
`scope_col == user.x` WHERE clause on top of that; the platform drops it as redundant
defensive double-filtering — which also removes the only place CRUD reached into
the principal. Org-scoping is the default by virtue of the org policy; a
one-user-per-org app is just a model carrying `UserScopedMixin`.
"""

import inspect
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, get_type_hints

from litestar import Controller, get, post
from litestar.exceptions import NotFoundException
from litestar.params import Dependency
from msgspec import Struct
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.actions.deps import ActionDeps
from app.platform.actions.registry import ActionRegistry
from app.platform.actions.schemas import ActionableDetail, ActionableList
from app.platform.base.filters import apply_filter, apply_sorts
from app.platform.base.models import BaseDBModel
from app.platform.base.registry import BaseRegistry
from app.platform.base.schemas import ListRequest, PagedResponse
from app.platform.base.search import SearchMixin, SearchRegistry
from app.platform.data.schemas import DataSchemaResponse, FieldSchema, TimeSeriesDataRequest, TimeSeriesDataResponse
from app.platform.data.service import FieldConfig, query_time_series_data
from app.platform.state_machine.roles import Actor
from app.platform.utils.sqids import Sqid

# Populated by make_crud_controller — exposed via GET /schema/crud-metadata for codegen.
_crud_metadata: dict[str, dict] = {}


@dataclass
class CRUDEntry:
    path: str
    config: "CRUDConfig"


class CRUDRegistry(BaseRegistry[type, CRUDEntry]):
    pass


@dataclass
class CRUDConfig[ModelT: BaseDBModel, ListT: ActionableList, DetailT: ActionableDetail]:
    """Declarative configuration for a resource's read endpoints."""

    model: type[ModelT]

    to_list_item: Callable[[ModelT, Actor[Any]], ListT]
    to_detail: Callable[[ModelT, Actor[Any]], DetailT]

    list_load_options: list[Any] = field(default_factory=list)
    detail_load_options: list[Any] = field(default_factory=list)

    filterable_columns: set[str] | None = None
    sortable_columns: set[str] | None = None
    default_sort: str | None = None  # e.g. "activity_date" — defaults to "created_at" desc

    # Label field used by entity combobox codegen
    label_field: str | None = None

    # Codegen metadata hints
    column_types: dict[str, str] = field(default_factory=dict)
    column_labels: dict[str, str] = field(default_factory=dict)

    # Custom filter handlers for columns that aren't direct model attributes.
    # Signature: (query, FilterDefinition) -> query
    custom_filters: dict[str, Callable] = field(default_factory=dict)

    extra_guards: list[Any] = field(default_factory=list)
    # Guards applied only to list (POST /) — on top of `extra_guards`.
    list_extra_guards: list[Any] = field(default_factory=list)
    # Guards applied only to detail (GET /{id}) — on top of `extra_guards`.
    detail_extra_guards: list[Any] = field(default_factory=list)

    # When False, don't generate the GET /{id} handler — the caller is
    # providing a custom detail handler (e.g. role-aware filtering).
    expose_detail: bool = True

    # Optional hook to modify the base query per-request (e.g. role-based scoping).
    # Signature: (query, user) -> query
    base_query_modifier: Callable[[Any, Actor[Any]], Any] | None = None

    # Time-series data endpoints — omit to skip generating POST /data and GET /data/schema.
    data_fields: list[FieldConfig] = field(default_factory=list)
    data_timestamp_field: str = "created_at"


def make_crud_controller[ModelT: BaseDBModel, ListT: ActionableList, DetailT: ActionableDetail](
    path: str,
    config: CRUDConfig[ModelT, ListT, DetailT],
    *,
    base_guards: Sequence[Any] = (),
) -> type[Controller]:
    """Generate a Litestar Controller with list (POST /) and detail (GET /{id}) routes.

    `base_guards` are applied to every route (e.g. the app's `requires_session`) —
    the platform injects them rather than importing the app's auth layer.
    """
    model = config.model
    guards = [*base_guards, *config.extra_guards]
    list_guards = [*guards, *config.list_extra_guards]
    detail_guards = [*guards, *config.detail_extra_guards]
    model_name = model.__name__

    default_sort_col = getattr(model, config.default_sort or "created_at")

    # Infer concrete return types from callable annotations for OpenAPI generation.
    # PEP 695 type params aren't resolved at runtime, so Litestar needs concrete types.
    hints = get_type_hints(config.to_list_item)
    list_item_type = hints.get("return", Struct)
    detail_hints = get_type_hints(config.to_detail)
    detail_type = detail_hints.get("return", Struct)
    _to_detail_wants_action_deps = "action_deps" in inspect.signature(config.to_detail).parameters

    # The action group is resolved lazily at request time — at controller-build
    # time the action registry may not yet be populated, since domain routes
    # are imported before the action router in the app factory.

    @post("/", guards=list_guards, tags=[model_name.lower()], status_code=200, operation_id=f"list_{model_name}")
    async def list_handler(
        self,
        data: ListRequest,
        user: Actor[Any] = Dependency(skip_validation=True),
        transaction: AsyncSession = Dependency(skip_validation=True),
        action_deps: ActionDeps | None = Dependency(default=None, skip_validation=True),
    ) -> PagedResponse:
        # Clamp limit and offset
        limit = max(1, min(data.limit, 200))
        offset = max(0, data.offset)

        # No scope WHERE clause — RLS scopes rows by org/user (D18).
        base = select(model)

        # Role-based query scoping
        if config.base_query_modifier is not None:
            base = config.base_query_modifier(base, user)

        # Load options
        for opt in config.list_load_options:
            base = base.options(opt)

        # Search
        if data.search and issubclass(model, SearchMixin):
            search_cond = model.search_filter(data.search)
            if search_cond is not None:
                base = base.where(search_cond)

        # Filters
        for f in data.filters:
            if f.column in config.custom_filters:
                base = config.custom_filters[f.column](base, f)
            else:
                base = apply_filter(base, model, f, config.filterable_columns)

        # Sorts (default: created_at desc)
        if data.sorts:
            base = apply_sorts(base, model, data.sorts, config.sortable_columns)
        else:
            base = base.order_by(default_sort_col.desc())

        # Count total
        count_q = select(func.count()).select_from(base.subquery())
        total = (await transaction.execute(count_q)).scalar_one()

        # Paginate
        paginated = base.offset(offset).limit(limit)
        result = await transaction.execute(paginated)
        rows = list(result.scalars().all())

        items = [config.to_list_item(row, user) for row in rows]

        if action_deps is not None:
            action_group = ActionRegistry().find_by_model(model)
            if action_group is not None:
                for item, row in zip(items, rows, strict=True):
                    item.actions = action_group.get_available_actions(action_deps, row)

        return PagedResponse(
            items=items,
            total=total,
            offset=offset,
            limit=limit,
            has_more=offset + len(items) < total,
        )

    list_handler.fn.__annotations__["return"] = PagedResponse[list_item_type]

    @get("/{id:str}", guards=detail_guards, tags=[model_name.lower()])
    async def detail_handler(
        self,
        id: Sqid,
        user: Actor[Any] = Dependency(skip_validation=True),
        transaction: AsyncSession = Dependency(skip_validation=True),
        action_deps: ActionDeps | None = Dependency(default=None, skip_validation=True),
    ) -> Struct:
        # Only the id predicate — RLS hides rows outside the caller's scope, so an
        # out-of-scope id resolves to None → 404 (no app-level scope check needed).
        query = select(model).where(model.id == id)
        if config.base_query_modifier is not None:
            query = config.base_query_modifier(query, user)
        for opt in config.detail_load_options:
            query = query.options(opt)

        result = await transaction.execute(query)
        obj = result.unique().scalar_one_or_none()
        if obj is None:
            raise NotFoundException()

        # `to_detail` may optionally declare an `action_deps` parameter — used by
        # resources that need to hydrate actions on nested objects (e.g. nested/child
        # objects). Detected by signature, so existing callers stay (obj, user).
        if _to_detail_wants_action_deps:
            detail = config.to_detail(obj, user, action_deps=action_deps)  # type: ignore[call-arg]
        else:
            detail = config.to_detail(obj, user)
        if action_deps is not None:
            action_group = ActionRegistry().find_by_model(model)
            if action_group is not None:
                detail.actions = action_group.get_available_actions(action_deps, obj)
        return detail

    detail_handler.fn.__annotations__["return"] = detail_type

    # Build controller class dynamically
    class_attrs: dict[str, Any] = {
        "path": path,
        "list_handler": list_handler,
    }
    if config.expose_detail:
        class_attrs["detail_handler"] = detail_handler

    if config.data_fields:
        _data_fields = config.data_fields
        _data_timestamp_field = config.data_timestamp_field

        @post("/data", guards=guards, status_code=200, operation_id=f"data_{model_name}")
        async def data_handler(
            self,
            data: TimeSeriesDataRequest,
            transaction: AsyncSession = Dependency(skip_validation=True),
        ) -> TimeSeriesDataResponse:
            # RLS scopes the rows; query_time_series_data takes no org_id (D18).
            return await query_time_series_data(transaction, model, _data_fields, data, _data_timestamp_field)

        @get("/data/schema", guards=guards, operation_id=f"data_schema_{model_name}")
        async def data_schema_handler(self) -> DataSchemaResponse:
            return DataSchemaResponse(
                fields=[
                    FieldSchema(
                        name=f.name,
                        label=f.label,
                        field_type=f.field_type,
                        aggregatable=f.aggregatable,
                        filterable=f.filterable,
                    )
                    for f in _data_fields
                ],
                timestamp_field=_data_timestamp_field,
            )

        class_attrs["data_handler"] = data_handler
        class_attrs["data_schema_handler"] = data_schema_handler

    controller_cls = type(
        f"{model_name}CRUDController",
        (Controller,),
        class_attrs,
    )

    # Register metadata for codegen (GET /schema/crud-metadata)
    # Auto-mark `*_cents` fields as currency so the frontend never renders raw cents.
    # Explicit values in CRUDConfig win — only fill in what the caller didn't set.
    column_types = dict(config.column_types)
    column_labels = dict(config.column_labels)
    list_fields = getattr(list_item_type, "__struct_fields__", ())
    for field_name in list_fields:
        if field_name.endswith("_cents"):
            column_types.setdefault(field_name, "currency")
            column_labels.setdefault(
                field_name,
                field_name.removesuffix("_cents").replace("_", " ").title() or "Amount",
            )

    metadata: dict[str, object] = {
        "filterable": sorted(config.filterable_columns or []),
        "sortable": sorted(config.sortable_columns or []),
    }
    if column_types:
        metadata["column_types"] = column_types
    if column_labels:
        metadata["column_labels"] = column_labels
    _crud_metadata[f"list_{model_name}"] = metadata

    CRUDRegistry().register(model, CRUDEntry(path=path, config=config))

    if issubclass(model, SearchMixin) and (model.trgm_columns or model.fts_columns):
        SearchRegistry[model.search_entity_type] = model

    return controller_cls
