"""Auth dependency providers.

The platform ships only `provide_auth_service` — it composes `AuthService` from the
app-provided `user_directory` + `magic_link_mailer` deps. The `user` /
`organization` principal providers stay app-side (they return the app's concrete
`User`/`Organization` off `request.user`).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.platform.auth.protocols import MagicLinkMailer, UserDirectory
from app.platform.auth.service import AuthService
from app.platform.utils.deps import dep


@dep("auth_service", sync_to_thread=False)
def provide_auth_service(
    transaction: AsyncSession,
    user_directory: UserDirectory,
    magic_link_mailer: MagicLinkMailer,
) -> AuthService:
    return AuthService(transaction, user_directory, magic_link_mailer, config)
