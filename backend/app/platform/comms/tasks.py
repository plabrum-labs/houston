"""Comms async tasks — outbound send.

The INBOUND email pipeline (`process_inbound_email_task` and the
app-specific inbound handlers) stays per-app: it routes on `User.inbox_local_part`
(an app-specific column) and enqueues domain tasks (e.g. a domain import task). The app
registers its own inbound task; the platform owns the generic outbound path.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.comms.clients.email import BaseEmailClient, EmailPayload, EmailSendError
from app.platform.comms.enums import CommsTaskName, MessageState
from app.platform.comms.models.messages import Message
from app.platform.comms.state_machine import message_state_machine
from app.platform.queue.registry import task
from app.platform.queue.transactions import with_transaction
from app.platform.queue.types import PlatformContext
from app.platform.state_machine.machine import StateMachineService

logger = logging.getLogger(__name__)


@task(CommsTaskName.SEND_EMAIL)
@with_transaction
async def send_email_task(
    ctx: PlatformContext,
    *,
    transaction: AsyncSession,
    email_client: BaseEmailClient,
    message_id: int,
) -> None:
    """Send a queued outbound message and transition it to SENT/FAILED."""
    record = await transaction.scalar(select(Message).where(Message.id == message_id))
    if record is None:
        raise ValueError(f"Message {message_id} not found")

    payload = EmailPayload(
        to=record.to_emails,
        subject=record.subject or "",
        body_html=record.body_html or "",
        body_text=record.body_text or "",
        from_email=record.from_email or "",
        from_name=record.from_name,
        reply_to=record.reply_to_email,
        in_reply_to=record.in_reply_to,
        references=record.in_reply_to,
        message_id=record.rfc_message_id,
    )

    sm_service = StateMachineService(transaction)
    try:
        ses_id = await email_client.send_email(payload)
        record.ses_message_id = ses_id
        record.sent_at = datetime.now(UTC)
        await sm_service.system_transition(message_state_machine, record, MessageState.SENT)
    except Exception as e:
        record.error_message = str(e)
        await sm_service.system_transition(message_state_machine, record, MessageState.FAILED)
        raise EmailSendError(str(e)) from e
