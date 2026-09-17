"""State machine models: StateMachineMixin and StateTransitionLog."""

from datetime import datetime
from enum import Enum
from typing import Any

import sqlalchemy as sa
from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.platform.base.models import BaseDBModel
from app.platform.utils.textenum import TextEnum


def get_state_machine_meta(model: type[BaseDBModel]) -> dict[str, Any] | None:
    """Return {column, states} if `model` has a state-machine `state` column."""
    state_col = model.__table__.columns.get("state")
    if state_col is None or not isinstance(state_col.type, TextEnum):
        return None
    return {
        "column": "state",
        "states": [v.value for v in state_col.type.enum_class],  # type: ignore[attr-defined]
    }


class _StateMachineMixinBase[E: Enum](BaseDBModel):
    __abstract__ = True
    state: Mapped[E]


def StateMachineMixin[E: Enum](  # noqa: N802
    *, state_enum: type[E], initial_state: E
) -> type[_StateMachineMixinBase[E]]:
    """Factory that returns an abstract mixin adding a `state` column.

    Usage:
        class Patient(StateMachineMixin(state_enum=PatientStatus, initial_state=PatientStatus.INTAKE_PENDING), ...):
            __tablename__ = "patients"
    """

    class _Mixin(_StateMachineMixinBase[E]):
        __abstract__ = True

        @declared_attr
        def state(cls) -> Mapped[E]:  # noqa: N805
            return mapped_column(
                TextEnum(state_enum),
                index=True,
                nullable=False,
                default=initial_state,
                server_default=initial_state.name,
            )

        def __init_subclass__(cls, **kwargs: Any) -> None:
            # Pin the concrete state type BEFORE super() triggers SQLAlchemy
            # mapping, so the mapper never sees the unresolved `Mapped[E]` TypeVar
            # inherited from _StateMachineMixinBase. (Surfaced by the example app.)
            if not cls.__dict__.get("__abstract__", False):
                cls.__annotations__["state"] = Mapped[state_enum]
            super().__init_subclass__(**kwargs)

    return _Mixin


class StateTransitionLog(BaseDBModel):
    """Append-only audit log. One row per completed transition."""

    __tablename__ = "state_transition_logs"

    object_type: Mapped[str] = mapped_column(String, nullable=False)
    object_id: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    from_state: Mapped[str] = mapped_column(String, nullable=False)
    to_state: Mapped[str] = mapped_column(String, nullable=False)
    actor_id: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    __table_args__ = (Index("ix_stl_object_lookup", "object_type", "object_id"),)
