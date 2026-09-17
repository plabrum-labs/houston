import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps
from typing import Any

from saq import CronJob
from saq.types import Function

# Task names are str-valued (the platform's framework TaskName and each app's own
# task enum are both StrEnum), so the registry accepts any str name.


@dataclass
class TaskRegistry:
    _tasks: list[Function] = field(default_factory=list)
    _scheduled_tasks: list[CronJob] = field(default_factory=list)

    def get_all_tasks(self) -> list[Function]:
        return list(self._tasks)

    def get_all_scheduled_tasks(self) -> list[CronJob]:
        return list(self._scheduled_tasks)

    def get_task_by_name(self, name: str) -> Callable[..., Any] | None:
        return next((t for t in self._tasks if t.__name__ == str(name)), None)


_registry = TaskRegistry()


def get_registry() -> TaskRegistry:
    return _registry


def task(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a SAQ task, injecting any param whose name matches a `ctx` key.

    `dispatch_task`'s QUEUE_SYNC branch only puts `config` in `ctx` (see its
    docstring), so a client kwarg declared here has nothing to pull from ctx
    under inline dispatch — the caller must pass it explicitly via
    `dispatch_task(..., **kwargs)` instead; an explicit kwarg always wins over
    the ctx lookup below.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        # Unwrap decorator stack (@with_transaction etc.) to inspect the real signature.
        original = inspect.unwrap(fn)
        injectable = set(inspect.signature(original).parameters)

        @wraps(fn)
        async def wrapper(ctx: Any, **kwargs: Any) -> Any:
            for key in injectable:
                if key not in kwargs and key in ctx:
                    kwargs[key] = ctx[key]
            return await fn(ctx, **kwargs)

        wrapper.__name__ = str(name)  # SAQ looks up tasks by __qualname__
        wrapper.__qualname__ = str(name)
        _registry._tasks.append(wrapper)
        return wrapper

    return decorator


def scheduled_task(cron: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        _registry._scheduled_tasks.append(CronJob(function=fn, cron=cron))
        return fn

    return decorator
