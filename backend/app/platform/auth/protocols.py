"""Auth protocols the app implements.

The app implements these against its concrete `User` + email service; the platform
names no concrete domain type.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.platform.state_machine.roles import Actor


@runtime_checkable
class UserDirectory(Protocol):
    """Looks up or creates the app's principal (an `Actor`) by email or id."""

    async def get_or_create_by_email(self, email: str) -> tuple[Actor[Any], bool]: ...

    async def get_by_id(self, user_id: int) -> Actor[Any] | None: ...

    async def mark_email_verified(self, user: Actor[Any]) -> None: ...


@runtime_checkable
class MagicLinkMailer(Protocol):
    """Narrow email interface so auth doesn't depend on the full `comms` port."""

    def validate_email_address(self, email: str) -> str: ...

    async def send_magic_link_email(
        self,
        *,
        user_id: int,
        to_email: str,
        magic_link_url: str,
        expires_minutes: int,
    ) -> None: ...
