"""Litestar entrypoint — `app.index:app` (matches `just dev-backend`).

Wires the houston platform over real HTTP: request → magic-link session auth →
RLS-scoped transaction → the app's `action_deps` → action/CRUD execution, all via
Litestar DI. Auth is `SessionAuth` over a Redis-backed server-side session: the cookie
holds only an opaque session id, whose payload is `{"user_id": ...}`; `retrieve_user_handler`
loads the `User` for that id on each request, and `provide_transaction` reads it to
`SET LOCAL` the RLS-scoped transaction.
"""

from pathlib import Path
from typing import Any

from advanced_alchemy.extensions.litestar import (
    AsyncSessionConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyPlugin,
)
from litestar import Litestar, get
from litestar.config.cors import CORSConfig
from litestar.connection import ASGIConnection
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.security.session_auth import SessionAuth
from litestar.stores.base import Store
from litestar.stores.redis import RedisStore
from litestar.template.config import TemplateConfig
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Config, config
from app.domain.apps.actions import AppActionGroupType
from app.domain.apps.routes import build_apps_controller
from app.domain.users.models import User
from app.domain.users.queries import get_user_by_id
from app.platform.actions.registry import ActionRegistry
from app.platform.actions.routes import build_action_router
from app.platform.auth.guards import requires_session
from app.platform.auth.routes import build_auth_router
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

ONE_DAY = 60 * 60 * 24


@get("/health", sync_to_thread=False, exclude_from_auth=True)
def health() -> dict[str, str]:
    return {"status": "ok"}


@get("/auth/me", guards=[requires_session], sync_to_thread=False)
def auth_me(user: User) -> dict[str, object]:
    """Current principal — proves auth + the RLS-scoped session boot end-to-end."""
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role.value}


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

    async def retrieve_user_handler(session: dict[str, Any], connection: ASGIConnection) -> User | None:
        # Runs inside the auth middleware, before request-scoped DI exists — so it opens
        # its own short-lived session. `expire_on_commit=False` keeps the loaded columns
        # readable on the detached instance `provide_transaction` later scopes RLS from.
        user_id = session.get("user_id")
        if not user_id:
            return None
        async with db_sessionmaker() as db:
            return await get_user_by_id(db, int(user_id))

    stores: dict[str, Store] = {"sessions": RedisStore.with_client(url=config.REDIS_URL)}
    session_auth = SessionAuth[User, Any](
        retrieve_user_handler=retrieve_user_handler,
        session_backend_config=ServerSideSessionConfig(
            store="sessions",
            samesite="lax",
            secure=not config.IS_DEV,
            httponly=True,
            max_age=ONE_DAY * 14,
        ),
        exclude=["^/schema"],  # keep OpenAPI public for orval codegen
    )

    route_handlers: list = [health, auth_me]

    # Import every deps.py + actions.py + tasks.py so their @dep providers, @action
    # groups, and @task handlers register on the global registries before
    # get_dependencies() / the routers below. `__file__` is app/index.py, so its parent
    # is the app package dir (the discovery root).
    discover_and_import(["deps.py", "actions.py", "tasks.py"], search_root=Path(__file__).parent)
    route_handlers += [
        build_auth_router(),
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
        on_app_init=[session_auth.on_app_init],
        stores=stores,
        cors_config=CORSConfig(allow_origins=[config.FRONTEND_ORIGIN], allow_credentials=True),
        template_config=TemplateConfig(directory=Path(config.EMAIL_TEMPLATES_DIR), engine=JinjaTemplateEngine),
        plugins=[sqlalchemy_plugin, SqidSchemaPlugin()],
        type_encoders={Sqid: sqid_enc_hook},
        type_decoders=[(sqid_type_predicate, sqid_dec_hook)],
    )
    litestar_app.state.db_sessionmaker = db_sessionmaker
    return litestar_app


app = create_app(config)
