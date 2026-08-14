"""DB helpers — create_model / update_model auto-emit lifecycle Events."""

from __future__ import annotations

import logging
from typing import Any

from msgspec import structs
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.base.models import BaseDBModel
from app.platform.base.schemas import BaseSchema
from app.platform.events.enums import EventType
from app.platform.events.schemas import CreatedEventData, UpdatedEventData, make_field_changes
from app.platform.events.service import emit_event

logger = logging.getLogger(__name__)


async def _emit_created_event(
    session: AsyncSession,
    obj: BaseDBModel,
    user_id: int,
    org_id: int,
    create_vals: BaseSchema,
    track_fields: list[str] | None,
) -> None:
    if track_fields is None:
        initial_values = {f: v for f, v in structs.asdict(create_vals).items() if v is not None}
    else:
        initial_values = {f: getattr(obj, f, None) for f in track_fields}

    await emit_event(
        session=session,
        event_type=EventType.CREATED,
        obj=obj,
        user_id=user_id,
        org_id=org_id,
        event_data=CreatedEventData(initial_values=initial_values),
    )


async def _emit_updated_event(
    session: AsyncSession,
    obj: BaseDBModel,
    user_id: int,
    org_id: int,
    old_values: dict[str, Any],
) -> None:
    new_values = {f: getattr(obj, f, None) for f in old_values if hasattr(obj, f)}
    changes = make_field_changes(old_values, new_values)
    if changes:
        await emit_event(
            session=session,
            event_type=EventType.UPDATED,
            obj=obj,
            user_id=user_id,
            org_id=org_id,
            event_data=UpdatedEventData(changes=changes),
        )


async def create_model[T: BaseDBModel](
    session: AsyncSession,
    org_id: int | None,
    model_class: type[T],
    create_vals: BaseSchema,
    user_id: int,
    ignore_fields: list[str] | None = None,
    should_track: bool = True,
    track_fields: list[str] | None = None,
) -> T:
    """Create a model instance from a struct DTO and emit a CREATED event."""
    ignore_fields = ignore_fields or []
    data = {f: v for f, v in structs.asdict(create_vals).items() if v is not None and f not in ignore_fields}
    if org_id is not None and hasattr(model_class, "organization_id"):
        data["organization_id"] = org_id

    obj = model_class(**data)
    session.add(obj)
    await session.flush()

    if should_track and org_id is not None:
        try:
            await _emit_created_event(session, obj, user_id, org_id, create_vals, track_fields)
        except Exception as e:
            logger.warning("Failed to emit CREATED event: %s", e)

    return obj


async def update_model[T: BaseDBModel](
    session: AsyncSession,
    model_instance: T,
    update_vals: BaseSchema,
    user_id: int,
    org_id: int | None,
    should_track: bool = True,
    track_fields: list[str] | None = None,
) -> T:
    """Apply struct updates to a model instance and emit an UPDATED event."""
    update_dict = structs.asdict(update_vals)
    fields_to_update: dict[str, Any] = {}
    for k, v in update_dict.items():
        if hasattr(v, "__struct_fields__"):
            fields_to_update[k] = structs.asdict(v)
        else:
            fields_to_update[k] = v

    old_values: dict[str, Any] | None = None
    if should_track and org_id is not None:
        if track_fields:
            fields_to_track = track_fields
        else:
            fields_to_track = [f for f in fields_to_update if not hasattr(model_instance, f"{f}_id")]
        old_values = {f: getattr(model_instance, f, None) for f in fields_to_track if hasattr(model_instance, f)}

    for field, value in fields_to_update.items():
        if not hasattr(model_instance, field):
            continue
        nested_id_field = f"{field}_id"
        if hasattr(model_instance, nested_id_field):
            if value is None:
                setattr(model_instance, nested_id_field, None)
            elif isinstance(value, dict):
                existing = getattr(model_instance, field, None)
                if existing:
                    for nf, nv in value.items():
                        if hasattr(existing, nf):
                            setattr(existing, nf, nv)
                else:
                    logger.warning("Cannot auto-create nested object for field '%s'", field)
            else:
                logger.warning("Unexpected value type for nested field '%s': %s", field, type(value))
        else:
            setattr(model_instance, field, value)

    await session.flush()

    if old_values is not None:
        try:
            await _emit_updated_event(session, model_instance, user_id, org_id, old_values)  # type: ignore[arg-type]
        except Exception as e:
            logger.warning("Failed to emit UPDATED event: %s", e)

    return model_instance
