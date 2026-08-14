"""Session auth backend (D19, option C).

The platform builds the Litestar `SessionAuth` from the app's `UserDirectory` and owns
the session-dict shape (`{"user_id": int}`, consistent with D3 + the RLS
`app.user_id` convention). The app provides the `UserDirectory`, the session
store/config, and the mount/exclude list.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from litestar.connection import ASGIConnection
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.security.session_auth import SessionAuth

from app.platform.auth.protocols import UserDirectory
from app.platform.state_machine.roles import Actor


def build_session_auth(
    *,
    directory: UserDirectory,
    session_config: ServerSideSessionConfig,
    exclude: Sequence[str] = (),
) -> SessionAuth[Actor[Any], Any]:
    async def retrieve_user_handler(
        session: dict[str, Any],
        connection: ASGIConnection,
    ) -> Actor[Any] | None:
        user_id = session.get("user_id")
        if user_id is None:
            return None
        return await directory.get_by_id(int(user_id))

    return SessionAuth(
        retrieve_user_handler=retrieve_user_handler,
        session_backend_config=session_config,
        exclude=list(exclude),
    )
