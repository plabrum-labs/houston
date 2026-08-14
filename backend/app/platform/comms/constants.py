"""Inbox local-part constants and canonicalization.

Both registration (claim) and inbound routing must apply the same normalization
so that what a user reserves matches what arrives in `To:`.
"""

import re

RESERVED_INBOX_LOCAL_PARTS: frozenset[str] = frozenset(
    {
        "support",
        "noreply",
        "no-reply",
        "mailer-daemon",
        "postmaster",
        "abuse",
        "webmaster",
        "root",
        "admin",
        "info",
        "hello",
        "billing",
        "security",
        "help",
        "contact",
        "sales",
        "team",
        "ops",
        "api",
    }
)

LOCAL_PART_MIN_LEN = 3
LOCAL_PART_MAX_LEN = 32

# Lowercase alnum + hyphen, no leading/trailing hyphen.
_LOCAL_PART_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")


def normalize_local_part(raw: str) -> str:
    """Canonical form: lowercase, no whitespace, no dots (Gmail-style)."""
    return raw.strip().lower().replace(".", "")


def is_valid_local_part_shape(canonical: str) -> bool:
    if not LOCAL_PART_MIN_LEN <= len(canonical) <= LOCAL_PART_MAX_LEN:
        return False
    return _LOCAL_PART_RE.match(canonical) is not None
