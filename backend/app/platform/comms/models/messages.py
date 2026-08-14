"""Unified messages model — inbound (SES → S3) and outbound (queued → SES)."""

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.base.models import BaseDBModel
from app.platform.base.rls_mixins import UserScopedMixin
from app.platform.comms.enums import MessageDirection, MessageState
from app.platform.utils.sqids import Sqid, SqidType
from app.platform.utils.textenum import TextEnum


class Message(UserScopedMixin, BaseDBModel):
    __tablename__ = "email_messages"

    user_id: Mapped[Sqid] = mapped_column(
        SqidType,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email_thread_id: Mapped[Sqid | None] = mapped_column(
        SqidType,
        sa.ForeignKey("email_threads.id", ondelete="SET NULL"),
        index=True,
    )
    direction: Mapped[MessageDirection] = mapped_column(TextEnum(MessageDirection), nullable=False)
    state: Mapped[MessageState] = mapped_column(TextEnum(MessageState), nullable=False)

    subject: Mapped[str | None] = mapped_column(sa.Text)
    body_text: Mapped[str | None] = mapped_column(sa.Text)
    body_html: Mapped[str | None] = mapped_column(sa.Text)
    from_email: Mapped[str | None] = mapped_column(sa.Text)
    from_name: Mapped[str | None] = mapped_column(sa.Text)
    to_emails: Mapped[list[str]] = mapped_column(sa.ARRAY(sa.Text), server_default="{}")
    ses_message_id: Mapped[str | None] = mapped_column(sa.Text, unique=True, index=True)
    rfc_message_id: Mapped[str | None] = mapped_column(sa.Text, unique=True, index=True)
    in_reply_to: Mapped[str | None] = mapped_column(sa.Text)
    attachments_json: Mapped[dict | None] = mapped_column(sa.JSON)

    read_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), index=True)

    # Inbound-only
    s3_bucket: Mapped[str | None] = mapped_column(sa.Text)
    # s3_key doubles as the idempotency key for SES re-deliveries
    s3_key: Mapped[str | None] = mapped_column(sa.Text, unique=True)
    received_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    spf_pass: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("false"), nullable=False)
    dkim_pass: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("false"), nullable=False)
    is_automated: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("false"), nullable=False)

    # Outbound-only
    reply_to_email: Mapped[str | None] = mapped_column(sa.Text)
    template_name: Mapped[str | None] = mapped_column(sa.Text)
    sent_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(sa.Text)

    __table_args__ = (
        sa.CheckConstraint(
            "(direction = 'OUT') OR (s3_key IS NOT NULL)",
            name="ck_inbound_has_s3_key",
        ),
        sa.Index("ix_email_messages_user_archived", "user_id", "archived_at"),
        sa.Index("ix_email_messages_user_thread", "user_id", "email_thread_id"),
    )

    @property
    def pdf_attachments(self) -> list[dict]:
        """Inbound PDF attachment metadata entries from `attachments_json`.

        Each entry is the dict written by the inbound-email processor and
        carries at least `filename`, `content_type`, `size`, and `s3_key`.
        """
        raw = self.attachments_json or {}
        items = raw.get("attachments") if isinstance(raw, dict) else None
        if not items:
            return []
        return [
            item
            for item in items
            if (item.get("content_type") or "").lower() == "application/pdf"
            or (item.get("filename") or "").lower().endswith(".pdf")
        ]
