"""Billing service dependency."""

from typing import Any

from app.config import config
from app.platform.billing.client import LocalBillingClient
from app.platform.billing.service import BillingService
from app.platform.state_machine.roles import Actor
from app.platform.utils.deps import dep

DEMO_ORG_ID = 0


@dep("billing_service", sync_to_thread=False)
def provide_billing_service(user: Actor[Any]) -> BillingService:
    if user.organization_id == DEMO_ORG_ID:
        return BillingService(LocalBillingClient())
    if config.IS_DEV or config.ENV == "testing" or not config.STRIPE_SECRET_KEY:
        return BillingService(LocalBillingClient())
    # Imported here, not at module scope, so a Local*-only app importing this
    # module (or anything under `app.platform.billing`) never needs `stripe` installed.
    from app.platform.billing.stripe_client import StripeBillingClient  # noqa: PLC0415

    return BillingService(StripeBillingClient(config))
