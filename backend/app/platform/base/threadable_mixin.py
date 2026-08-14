"""Mixin for models that can have threads."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import and_
from sqlalchemy.orm import Mapped, declared_attr, relationship

if TYPE_CHECKING:
    from app.platform.threads.models import Thread
    from app.platform.threads.schemas import ThreadUnreadInfo


class ThreadableMixin:
    """Polymorphic Thread relationship for any object that can host messages.

    The thread is keyed by `(threadable_type, threadable_id)` where
    `threadable_type` is the parent's table name. Threads are created lazily
    when the first message is posted.
    """

    @declared_attr
    @classmethod
    def thread(cls: Any) -> Mapped["Thread | None"]:
        from app.platform.threads.models import Thread  # noqa: PLC0415

        tablename: str = cls.__tablename__

        return relationship(
            "Thread",
            primaryjoin=lambda: and_(
                Thread.threadable_type == tablename,
                Thread.threadable_id == cls.id,
            ),
            foreign_keys="[Thread.threadable_id]",
            viewonly=True,
            uselist=False,
            lazy="selectin",
        )

    def get_thread_unread_info(self, user_id: int) -> "ThreadUnreadInfo | None":
        """Compute unread info from an already-loaded thread relationship."""
        from app.platform.threads.schemas import ThreadUnreadInfo  # noqa: PLC0415
        from app.platform.utils.sqids import Sqid  # noqa: PLC0415

        if self.thread is None:
            return None

        last_read_at = None
        for read_status in self.thread.read_statuses:
            if read_status.user_id == user_id:
                if last_read_at is None or read_status.read_at > last_read_at:
                    last_read_at = read_status.read_at

        unread_count = 0
        for message in self.thread.messages:
            if last_read_at is None or message.created_at > last_read_at:
                unread_count += 1

        return ThreadUnreadInfo(
            thread_id=Sqid(self.thread.id),
            unread_count=unread_count,
        )
