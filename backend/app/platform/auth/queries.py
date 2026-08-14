from datetime import datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.auth.models import MagicLinkToken

# Allow recently-used tokens to be re-verified (handles React StrictMode double-mounts)
_IDEMPOTENCY_WINDOW = timedelta(seconds=60)


async def get_valid_magic_link_token(db: AsyncSession, token_hash: str, now: datetime) -> MagicLinkToken | None:
    result = await db.execute(
        select(MagicLinkToken).where(
            MagicLinkToken.token_hash == token_hash,
            MagicLinkToken.expires_at > now,
            or_(
                MagicLinkToken.used_at.is_(None),
                MagicLinkToken.used_at > now - _IDEMPOTENCY_WINDOW,
            ),
        )
    )
    return result.scalar_one_or_none()


async def create_magic_link_token(
    db: AsyncSession, *, token_hash: str, user_id: int, expires_at: datetime
) -> MagicLinkToken:
    token = MagicLinkToken(token_hash=token_hash, user_id=user_id, expires_at=expires_at)
    db.add(token)
    await db.flush()
    return token
