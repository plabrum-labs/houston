"""Generic auth routes — magic-link request / verify / logout.

The demo-login shortcut (app-specific emails) and `/me` (hydrates an app-specific
profile/domain model) stay per-app (D19); the app mounts them alongside this router.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from litestar import Request, Router, get, post
from litestar.exceptions import PermissionDeniedException
from litestar.middleware.rate_limit import RateLimitConfig
from litestar.types import Guard

from app.platform.auth.service import AuthService

logger = logging.getLogger(__name__)

_rate_limit = RateLimitConfig(rate_limit=("minute", 3))


@dataclass
class MagicLinkRequestBody:
    email: str


@post("/magic-link/request", tags=["auth"], middleware=[_rate_limit.middleware], exclude_from_auth=True)
async def request_magic_link(
    data: MagicLinkRequestBody,
    auth_service: AuthService,
) -> dict[str, str]:
    """Request a magic link."""
    try:
        await auth_service.request_magic_link(data.email)
    except Exception:
        logger.exception("Failed to send magic link to %s", data.email)
    return {"message": "If that email exists, a magic link has been sent."}


@get("/magic-link/verify", tags=["auth"], exclude_from_auth=True)
async def verify_magic_link(
    token: str,
    request: Request,
    auth_service: AuthService,
) -> dict[str, str]:
    """Verify a magic link token and set session."""
    existing_user_id = request.session.get("user_id")
    user = await auth_service.verify_magic_link(token)

    if user is not None:
        request.set_session({"user_id": int(user.id)})
        return {"message": "Authenticated"}
    if existing_user_id is not None:
        return {"message": "Already authenticated"}

    raise PermissionDeniedException("Invalid or expired magic link.")


@post("/logout", tags=["auth"], exclude_from_auth=True)
async def logout(request: Request) -> dict[str, str]:
    """Clear the current session."""
    request.clear_session()
    return {"message": "Logged out"}


def build_auth_router(*, path: str = "/auth", guards: Sequence[Guard] = ()) -> Router:
    return Router(
        path=path,
        route_handlers=[request_magic_link, verify_magic_link, logout],
        guards=list(guards),
        tags=["auth"],
    )
