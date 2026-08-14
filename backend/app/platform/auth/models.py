from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.base.models import BaseDBModel


class MagicLinkToken(BaseDBModel):
    __tablename__ = "magic_link_tokens"

    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthUserMixin(BaseDBModel):
    """Abstract mixin with the magic-link auth columns (`email`, `email_verified_at`).

    Apps compose this alongside `app.platform.users.models.UserMixin` on their
    concrete `User` to get magic-link auth "for free":

        class User(UserMixin(role_enum=Role, default_role=Role.CLIENT), AuthUserMixin):
            __tablename__ = "users"
            name: Mapped[str] = mapped_column(sa.Text)
    """

    __abstract__ = True

    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
