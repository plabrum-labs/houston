from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.base.models import BaseDBModel


class _SequenceMixinBase(BaseDBModel):
    __abstract__ = True

    # The app supplies its own SequenceType enum member; the platform stores its `.name`.
    sequence_type: ClassVar[Enum]
    sequence_prefix: ClassVar[str]
    sequence_padding: ClassVar[int]
    sequence_start_value: ClassVar[int]
    organization_id: Mapped[int]
    identifier: Mapped[str | None]


def SequenceMixin(  # noqa: N802
    *,
    sequence_type: Enum,
    prefix: str,
    padding: int = 4,
    start_value: int = 1_000,
) -> type[_SequenceMixinBase]:
    """Factory that returns a mixin adding a per-org auto-incrementing `identifier`.

    `sequence_type` is a member of the *app's own* SequenceType enum (the platform owns
    the mechanism, not the values). Usage:

        class Invoice(
            SequenceMixin(sequence_type=AppSequenceType.invoice_number, prefix="INV"),
            ...,
        ):
            ...
    """
    _sequence_type = sequence_type
    _prefix = prefix
    _padding = padding
    _start_value = start_value

    class _Mixin(_SequenceMixinBase):
        __abstract__ = True

        sequence_type: ClassVar[Enum] = _sequence_type
        sequence_prefix: ClassVar[str] = _prefix
        sequence_padding: ClassVar[int] = _padding
        sequence_start_value: ClassVar[int] = _start_value

        identifier: Mapped[str | None] = mapped_column(sa.Text)

        def __init_subclass__(cls, **kwargs: Any) -> None:
            super().__init_subclass__(**kwargs)
            if "identifier" in cls.__table__.c and "organization_id" in cls.__table__.c:
                sa.Index(
                    f"ix_{cls.__tablename__}_org_identifier",
                    cls.__table__.c.organization_id,
                    cls.__table__.c.identifier,
                    unique=True,
                    postgresql_where=cls.__table__.c.identifier.isnot(None),
                )

    return _Mixin
