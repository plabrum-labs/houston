from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.platform.base.models import BaseDBModel
from app.platform.base.rls_mixins import UserScopedMixin
from app.platform.dashboard.enums import WidgetType
from app.platform.utils.sqids import Sqid, SqidType
from app.platform.utils.textenum import TextEnum


class Dashboard(UserScopedMixin, BaseDBModel):
    __tablename__ = "dashboards"

    user_id: Mapped[Sqid] = mapped_column(
        SqidType,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    widgets: Mapped[list[Widget]] = relationship(
        back_populates="dashboard",
        cascade="all, delete-orphan",
        order_by="Widget.position_y, Widget.position_x, Widget.id",
        lazy="noload",
    )


class Widget(UserScopedMixin, BaseDBModel):
    __tablename__ = "widgets"

    dashboard_id: Mapped[Sqid] = mapped_column(
        SqidType,
        sa.ForeignKey("dashboards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Sqid] = mapped_column(
        SqidType,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[WidgetType] = mapped_column(TextEnum(WidgetType), nullable=False)
    title: Mapped[str] = mapped_column(sa.Text, nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    query: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )
    position_x: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    position_y: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    size_w: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("1"))
    size_h: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("1"))

    dashboard: Mapped[Dashboard] = relationship(back_populates="widgets", lazy="raise")
