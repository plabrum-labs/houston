"""Media model — image/video uploads with thumbnail post-processing."""

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.base.models import BaseDBModel
from app.platform.base.rls_mixins import OrgScopedMixin
from app.platform.base.threadable_mixin import ThreadableMixin
from app.platform.media.enums import MediaStates
from app.platform.state_machine.models import StateMachineMixin


class Media(
    OrgScopedMixin,
    ThreadableMixin,
    StateMachineMixin(state_enum=MediaStates, initial_state=MediaStates.PENDING),
    BaseDBModel,
):
    """Image or video upload with optional generated thumbnail."""

    __tablename__ = "media"

    organization_id: Mapped[int] = mapped_column(
        sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    file_key: Mapped[str] = mapped_column(sa.Text, nullable=False, unique=True)
    file_name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    file_type: Mapped[str] = mapped_column(sa.Text, nullable=False)  # 'image' or 'video'
    file_size: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(sa.Text, nullable=False)

    thumbnail_key: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
