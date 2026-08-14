"""Email client abstraction + dev stub.

The platform ships the abstract `BaseEmailClient` and the `LocalEmailClient` dev stub.
The concrete provider client (the source app's `SESEmailClient`, which reads
`SES_REGION`/`SES_CONFIGURATION_SET` and depends on `aioboto3`) is wired app-side
and injected via `PlatformContext` — the platform types against the base and never
instantiates a provider.
"""

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.platform.queue.exceptions import CommittableTaskError

logger = logging.getLogger(__name__)


class EmailSendError(CommittableTaskError):
    """Raised when an email client fails to deliver a message."""


@dataclass
class EmailPayload:
    """Email payload passed to the underlying client."""

    to: list[str]
    subject: str
    body_html: str
    body_text: str
    from_email: str
    from_name: str | None = None
    reply_to: str | None = None
    in_reply_to: str | None = None
    references: str | None = None
    message_id: str | None = None


class BaseEmailClient(ABC):
    @abstractmethod
    async def send_email(self, message: EmailPayload) -> str:
        """Send an email. Returns the provider's message ID."""


class LocalEmailClient(BaseEmailClient):
    """Logs the email instead of sending — used for dev and tests."""

    async def send_email(self, message: EmailPayload) -> str:
        from_header = f'"{message.from_name}" <{message.from_email}>' if message.from_name else message.from_email

        logger.info("=" * 80)
        logger.info("LOCAL EMAIL (not actually sent)")
        logger.info(f"To: {', '.join(message.to)}")
        logger.info(f"From: {from_header}")
        logger.info(f"Subject: {message.subject}")
        logger.info(f"Reply-To: {message.reply_to}")
        logger.info(f"Message-ID: {message.message_id}")
        logger.info(f"In-Reply-To: {message.in_reply_to}")
        logger.info(f"References: {message.references}")
        logger.info("-" * 80)
        logger.info("Text Body")
        logger.info(message.body_text)
        logger.info("=" * 80)

        return f"local-{uuid.uuid4()}"
