from __future__ import annotations

from enum import Enum

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.sequences.mixins import _SequenceMixinBase
from app.platform.sequences.models import BusinessSequence


async def generate_next_identifier(
    transaction: AsyncSession,
    organization_id: int,
    sequence_type: Enum,
    start_value: int,
    prefix: str,
    padding: int,
) -> str:
    """Atomically issue the next identifier for (organization_id, sequence_type)."""
    insert_stmt = (
        pg_insert(BusinessSequence)
        .values(
            organization_id=organization_id,
            type=sequence_type.name,
            current_value=start_value,
        )
        .on_conflict_do_nothing(index_elements=["organization_id", "type"])
    )
    await transaction.execute(insert_stmt)

    update_stmt = (
        sa.update(BusinessSequence)
        .where(
            BusinessSequence.organization_id == organization_id,
            # `type` is a plain str column now, so compare against the key explicitly.
            BusinessSequence.type == sequence_type.name,
        )
        .values(current_value=BusinessSequence.current_value + 1)
        .returning(BusinessSequence.current_value)
    )
    result = await transaction.execute(update_stmt)
    next_value = result.scalar_one()
    return f"{prefix}-{str(next_value).rjust(padding, '0')}"


async def assign_identifier_if_missing(transaction: AsyncSession, obj: _SequenceMixinBase) -> None:
    if obj.identifier is not None:
        return
    obj.identifier = await generate_next_identifier(
        transaction,
        obj.organization_id,
        obj.sequence_type,
        obj.sequence_start_value,
        obj.sequence_prefix,
        obj.sequence_padding,
    )
