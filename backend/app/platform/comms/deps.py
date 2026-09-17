from litestar import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.comms.clients.email import BaseEmailClient, LocalEmailClient
from app.platform.comms.service.emails import EmailService
from app.platform.utils.deps import dep


@dep("email_client", sync_to_thread=False)
def provide_email_client() -> BaseEmailClient:
    # Dev/test logs the email instead of sending. The provider SES client is app-side
    # and wired later (prod), so there is no other client to choose here yet.
    return LocalEmailClient()


@dep("email_service")
async def provide_email_service(
    request: Request, transaction: AsyncSession, email_client: BaseEmailClient
) -> EmailService:
    return EmailService(request.app.template_engine, transaction, request, email_client)  # type: ignore[arg-type]
