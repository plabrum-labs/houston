"""Auth dependency providers.

`provide_auth_service` composes the flat `AuthService` from the app's `email_service`
(provided by `app.platform.comms.deps`) and looks users up directly against the
concrete `User` model. The `user` / `organization` principal providers stay app-side
(`app/deps.py`) — they return the concrete `User`/`Organization` off `request.user`.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.platform.auth.service import AuthService
from app.platform.comms.service.emails import EmailService
from app.platform.utils.deps import dep


@dep("auth_service", sync_to_thread=False)
def provide_auth_service(transaction: AsyncSession, email_service: EmailService) -> AuthService:
    return AuthService(transaction, email_service, config)
