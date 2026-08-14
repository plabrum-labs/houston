"""Litestar entrypoint — `app.index:app` (matches `just dev-backend`).

Wires the houston platform over real HTTP: request → auth (X-User-Id dev shim) →
RLS-scoped transaction → the app's `action_deps` → action/CRUD execution, all via
Litestar DI. The header-auth middleware is a DEV SHIM — replace it with the ported
`app.platform.auth` (magic-link sessions) once that path is wired.
"""

from pathlib import Path

from advanced_alchemy.extensions.litestar import (
    AsyncSessionConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyPlugin,
)
from litestar import Litestar, Request, get
from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException
from litestar.handlers.base import BaseRouteHandler
from litestar.middleware import DefineMiddleware
from litestar.middleware.authentication import (
    AbstractAuthenticationMiddleware,
    AuthenticationResult,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Config, config
from app.domain.apps.actions import AppActionGroupType
from app.domain.apps.routes import build_apps_controller
from app.domain.users.models import User
from app.platform.actions.registry import ActionRegistry
from app.platform.actions.routes import build_action_router
from app.platform.base.schema_routes import build_schema_router
from app.platform.base.search_routes import build_search_router
from app.platform.utils.deps import get_dependencies
from app.platform.utils.discovery import discover_and_import
from app.platform.utils.sqids import (
    Sqid,
    SqidSchemaPlugin,
    sqid_dec_hook,
    sqid_enc_hook,
    sqid_type_predicate,
)


def requires_session(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """Guard: requires an authenticated session."""
    if not connection.user:
        raise NotAuthorizedException("Authentication required")


class HeaderAuthMiddleware(AbstractAuthenticationMiddleware):
    """DEV SHIM: reads `X-User-Id`, loads the User in a system-mode session, sets scope.

    Replace with the ported `app.platform.auth` (magic-link sessions) for anything real.
    The load runs in system mode so the lookup isn't itself blocked by RLS; then
    `provide_transaction` reads `request.user` to `SET LOCAL` the scoped transaction.
    """

    async def authenticate_request(self, connection: ASGIConnection) -> AuthenticationResult:
        user_id = connection.headers.get("X-User-Id")
        if not user_id:
            return AuthenticationResult(user=None, auth=None)

        sessionmaker = connection.app.state.db_sessionmaker
        async with sessionmaker() as session:
            async with session.begin():
                await session.execute(text("SELECT set_config('app.is_system_mode', 'true', true)"))
                user = await session.get(User, int(user_id))
                if user is not None:
                    session.expunge(user)

        return AuthenticationResult(user=user, auth=None)


@get("/health", sync_to_thread=False)
def health() -> dict[str, str]:
    return {"status": "ok"}


@get("/me", guards=[requires_session], sync_to_thread=False)
def me(request: Request) -> dict[str, object]:
    """Current principal — proves auth + the RLS-scoped session boot end-to-end."""
    user = request.user
    return {"id": user.id, "name": user.name, "role": user.role.value}


def create_app(config: Config = config) -> Litestar:
    engine = create_async_engine(config.ASYNC_DATABASE_URL)
    db_sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    sqlalchemy_plugin = SQLAlchemyPlugin(
        config=SQLAlchemyAsyncConfig(
            engine_instance=engine,
            session_config=AsyncSessionConfig(expire_on_commit=False, autoflush=False),
            create_all=False,
        )
    )

    route_handlers: list = [health, me]

    # Import every deps.py + actions.py so their @dep providers and @action groups
    # register on the global registries before get_dependencies() / the routers below.
    # `__file__` is app/index.py, so its parent is the app package dir (the discovery root).
    discover_and_import(["deps.py", "actions.py"], search_root=Path(__file__).parent)
    route_handlers += [
        build_action_router(
            registry=ActionRegistry(),
            group_enum=AppActionGroupType,
            guards=[requires_session],
        ),
        build_apps_controller(base_guards=[requires_session]),
        build_schema_router(),
        build_search_router(guards=[requires_session]),
    ]

    litestar_app = Litestar(
        route_handlers=route_handlers,
        dependencies=get_dependencies(),
        middleware=[DefineMiddleware(HeaderAuthMiddleware, exclude=["^/schema"])],
        plugins=[sqlalchemy_plugin, SqidSchemaPlugin()],
        type_encoders={Sqid: sqid_enc_hook},
        type_decoders=[(sqid_type_predicate, sqid_dec_hook)],
    )
    litestar_app.state.db_sessionmaker = db_sessionmaker
    return litestar_app


app = create_app(config)
