"""Email thread model — groups related inbound and outbound messages per user."""

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, column_property, declared_attr, mapped_column, relationship, remote

from app.platform.base.models import BaseDBModel
from app.platform.base.rls_mixins import UserScopedMixin
from app.platform.comms.enums import MessageDirection
from app.platform.comms.models.messages import Message
from app.platform.utils.sqids import Sqid, SqidType


class EmailThread(UserScopedMixin, BaseDBModel):
    __tablename__ = "email_threads"

    user_id: Mapped[Sqid] = mapped_column(
        SqidType,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject: Mapped[str | None] = mapped_column(sa.Text)
    archived_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), index=True)

    # Correlated subquery picks the newest message id per thread; the relationship
    # joins on that id so joinedload produces a single LEFT OUTER JOIN.
    # user_id is included so Postgres can use ix_email_messages_user_thread.
    latest_message: Mapped[Message | None] = relationship(
        Message,
        primaryjoin=lambda: sa.and_(
            remote(Message.email_thread_id) == EmailThread.id,
            Message.id
            == (
                sa.select(Message.id)
                .where(
                    Message.user_id == EmailThread.user_id,
                    Message.email_thread_id == EmailThread.id,
                )
                .order_by(Message.created_at.desc())
                .limit(1)
                .correlate(EmailThread)
                .scalar_subquery()
            ),
        ),
        foreign_keys=lambda: [Message.email_thread_id],
        uselist=False,
        viewonly=True,
        lazy="noload",
    )

    @declared_attr
    def unread_count(cls) -> Mapped[int]:  # noqa: N805
        return column_property(
            sa.select(sa.func.count(Message.id))
            .where(
                Message.user_id == cls.user_id,
                Message.email_thread_id == cls.id,
                Message.direction == MessageDirection.IN,
                Message.read_at.is_(None),
                Message.archived_at.is_(None),
            )
            .correlate_except(Message)
            .scalar_subquery(),
            deferred=True,
        )

    @hybrid_property
    def has_unread_inbound(self) -> bool:
        return (self.unread_count or 0) > 0

    @has_unread_inbound.inplace.expression
    @classmethod
    def _has_unread_inbound_expr(cls):
        return sa.exists().where(
            Message.user_id == cls.user_id,
            Message.email_thread_id == cls.id,
            Message.direction == MessageDirection.IN,
            Message.read_at.is_(None),
            Message.archived_at.is_(None),
        )

    @hybrid_property
    def has_outbound(self) -> bool:
        msg = self.latest_message
        return msg is not None and msg.direction == MessageDirection.OUT

    @has_outbound.inplace.expression
    @classmethod
    def _has_outbound_expr(cls):
        return sa.exists().where(
            Message.user_id == cls.user_id,
            Message.email_thread_id == cls.id,
            Message.direction == MessageDirection.OUT,
        )
