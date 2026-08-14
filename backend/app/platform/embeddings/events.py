"""SQLAlchemy listeners that enqueue embedding tasks after commit.

Why after_commit and not after_flush:
  - Tasks must not run before the row is durable.
  - PK reads are reliable post-commit regardless of default-generation mode.
  - Rollbacks naturally drop the pending list.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm import Session, object_session

from app.platform.embeddings.enums import EmbeddingTaskName

logger = logging.getLogger(__name__)

_PENDING_KEY = "_pending_embeds"

# Resolver set by the app at startup. Tests override via set_queue_resolver().
# Returns the SAQ queue for the "default" queue, or None when unavailable
# (in which case enqueue is silently skipped — sweeper is the backstop).
_queue_resolver: Callable[[], Any] | None = None


def set_queue_resolver(resolver: Callable[[], Any] | None) -> None:
    global _queue_resolver
    _queue_resolver = resolver


def stage_embed_after_insert(_mapper: Any, _connection: Any, target: Any) -> None:
    _stage(target)


def stage_embed_after_update(_mapper: Any, _connection: Any, target: Any) -> None:
    state = sa.inspect(target)
    dirty_cols = {a.key for a in state.attrs if a.history.has_changes()}
    if not (dirty_cols & set(type(target).embedding_columns)):
        return
    _stage(target)


def _stage(target: Any) -> None:
    session = object_session(target)
    if session is None:
        return
    pending: list[Any] = session.info.setdefault(_PENDING_KEY, [])
    pending.append(target)


@event.listens_for(Session, "after_commit")
def _flush_pending_embeds(session: Session) -> None:
    pending: list[Any] = session.info.pop(_PENDING_KEY, [])
    if not pending:
        return
    resolver = _queue_resolver
    if resolver is None:
        return
    try:
        queue = resolver()
    except Exception:
        logger.exception("embeddings: queue resolver failed; skipping enqueue")
        return
    if queue is None:
        return
    for target in pending:
        try:
            coro = queue.enqueue(
                str(EmbeddingTaskName.EMBED_ROW),
                table=target.__tablename__,
                id=int(target.id),
            )
            if asyncio.iscoroutine(coro):
                asyncio.ensure_future(coro)
        except Exception:
            logger.exception("embeddings: failed to enqueue embed_row_task")


@event.listens_for(Session, "after_rollback")
def _drop_pending_embeds(session: Session) -> None:
    session.info.pop(_PENDING_KEY, None)
