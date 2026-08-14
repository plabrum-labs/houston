"""Email service — template rendering + queued dispatch."""

import logging
from typing import Any

from email_validator import EmailNotValidError, validate_email
from litestar import Request
from litestar.contrib.jinja import JinjaTemplateEngine
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.platform.comms.enums import CommsTaskName, MessageDirection, MessageState
from app.platform.comms.models.messages import Message
from app.platform.queue.transactions import dispatch_task

logger = logging.getLogger(__name__)


class EmailService:
    """High-level email service: validates addresses, renders templates, persists
    a Message row, and enqueues the SEND_EMAIL task after commit."""

    def __init__(self, template_engine: JinjaTemplateEngine, transaction: AsyncSession, request: Request):
        self.template_engine = template_engine
        self.transaction = transaction
        self.request = request

    def validate_email_address(self, email: str) -> str:
        try:
            valid = validate_email(email, check_deliverability=False)
            return valid.normalized
        except EmailNotValidError as e:
            raise ValueError(f"Invalid email address: {email}") from e

    def render_template(self, template_name: str, context: dict[str, Any]) -> tuple[str, str]:
        """Render email template, returning (html, text)."""
        jinja_env = self.template_engine.engine
        html_body = jinja_env.get_template(f"{template_name}/html.jinja2").render(**context)
        text_body = jinja_env.get_template(f"{template_name}/text.jinja2").render(**context)
        return html_body, text_body

    async def send_email(
        self,
        *,
        user_id: int,
        to: list[str] | str,
        subject: str,
        template_name: str,
        context: dict[str, Any],
        from_email: str | None = None,
        from_name: str | None = None,
        reply_to: str | None = None,
        email_thread_id: int | None = None,
        in_reply_to: str | None = None,
    ) -> int:
        if isinstance(to, str):
            to = [to]
        to = [self.validate_email_address(email) for email in to]

        from_email = from_email or config.SES_FROM_EMAIL
        from_name = from_name or config.SES_FROM_NAME
        reply_to = reply_to or config.SES_REPLY_TO_EMAIL or None

        html_body, text_body = self.render_template(template_name, context)

        record = Message(
            user_id=user_id,
            email_thread_id=email_thread_id,
            direction=MessageDirection.OUT,
            state=MessageState.QUEUED,
            to_emails=to,
            from_email=from_email,
            from_name=from_name,
            reply_to_email=reply_to,
            subject=subject,
            body_html=html_body,
            body_text=text_body,
            template_name=template_name,
            in_reply_to=in_reply_to,
        )
        self.transaction.add(record)
        await self.transaction.flush()

        await dispatch_task(self.transaction, self.request, CommsTaskName.SEND_EMAIL, message_id=record.id)
        return record.id

    async def send_magic_link_email(
        self,
        *,
        user_id: int,
        to_email: str,
        magic_link_url: str,
        expires_minutes: int = 15,
    ) -> None:
        product_name = config.PRODUCT_NAME
        await self.send_email(
            user_id=user_id,
            to=to_email,
            subject=f"Sign in to {product_name}",
            template_name="magic_link",
            context={
                "magic_link_url": magic_link_url,
                "expiration_minutes": expires_minutes,
            },
        )
