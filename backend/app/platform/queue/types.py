"""Typed SAQ context owned by app.platform.

The platform ships the minimal framework context its mechanism needs. Clients and other
app resources are provided in the app's queue/config.py startup hook (set as ctx
keys) and reach tasks via the `@task` decorator's DI — a task declares a typed
keyword param (e.g. `s3_client: BaseS3Client`) and the wrapper injects the
matching ctx value. Apps that also want them statically typed can extend:

    class AppContext(PlatformContext):
        s3_client: Required[BaseS3Client]
"""

from typing import Required

from saq.queue import Queue
from saq.types import Context
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.config import Config


class PlatformContext(Context):
    db_engine: Required[AsyncEngine]
    db_sessionmaker: Required[async_sessionmaker[AsyncSession]]
    config: Required[Config]
    queue: Required[Queue]
