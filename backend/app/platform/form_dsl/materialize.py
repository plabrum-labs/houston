"""Materialize a TemplateDefinition into form_nodes rows for any owner."""

from __future__ import annotations

from typing import Any

import msgspec
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.form_dsl.enums import FormNodeKind
from app.platform.form_dsl.models import FormNode
from app.platform.form_dsl.schema import FieldDef, FieldType, Section, TemplateDefinition


async def materialize_form_response(
    transaction: AsyncSession,
    owner: Any,
    owner_type: str,
    definition: dict | TemplateDefinition,
) -> int:
    """Walk `definition` and insert one FormNode per template node under
    `(owner_type, owner.id)`. Repeater shells are inserted; instances are
    created at runtime. Returns the template version, so the caller can pin
    it on the owner."""

    defn = definition if isinstance(definition, TemplateDefinition) else msgspec.convert(definition, TemplateDefinition)

    for section_index, section in enumerate(defn.sections):
        section_node = _section_node(owner, owner_type, section=section, sort_order=section_index)
        transaction.add(section_node)
        await transaction.flush()

        await _materialize_fields(transaction, owner, owner_type, section_node.id, section.fields)

    return defn.version


async def _materialize_fields(
    transaction: AsyncSession,
    owner: Any,
    owner_type: str,
    parent_id: int,
    fields: list[FieldDef],
    order_start: int = 0,
) -> None:
    for order, field in enumerate(fields, start=order_start):
        field_node = _field_node(owner, owner_type, parent_id=parent_id, field=field, sort_order=order)
        transaction.add(field_node)

        if field.type == FieldType.GROUP:
            await transaction.flush()
            await _materialize_fields(transaction, owner, owner_type, field_node.id, field.fields)


def _section_node(owner: Any, owner_type: str, *, section: Section, sort_order: int) -> FormNode:
    return FormNode(
        organization_id=owner.organization_id,
        owner_type=owner_type,
        owner_id=owner.id,
        parent_id=None,
        kind=FormNodeKind.section,
        schema_ref=section.id,
        label=section.title,
        config={"condition": msgspec.to_builtins(section.condition)} if section.condition else None,
        sort_order=sort_order,
    )


def _field_node(
    owner: Any,
    owner_type: str,
    *,
    parent_id: int | None,
    field: FieldDef,
    sort_order: int,
) -> FormNode:
    return FormNode(
        organization_id=owner.organization_id,
        owner_type=owner_type,
        owner_id=owner.id,
        parent_id=parent_id,
        kind=FormNodeKind.field,
        schema_ref=field.id,
        label=field.label,
        value=None,
        config=msgspec.to_builtins(field),
        sort_order=sort_order,
    )
