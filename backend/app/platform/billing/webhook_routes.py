"""Billing webhook routes — receives events from Stripe.

The split: the platform owns the generic Stripe plumbing — signature
verification and the routing/dispatch scaffold. The per-event domain handlers
(e.g. `invoice.payment_succeeded` → mutate a domain state machine) name
`app/domain/*` models, so they CANNOT live here; they register against the
channel registries below from app code. This mirrors the events/actions
registries: the platform owns the dispatcher, the app owns the handlers.
"""

import logging
from collections.abc import Awaitable, Callable

import stripe
from litestar import Request, Router, post
from litestar.exceptions import NotAuthorizedException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config

logger = logging.getLogger(__name__)

WebhookHandler = Callable[[stripe.Event, AsyncSession], Awaitable[None]]


class BillingWebhookRegistry:
    """Domain webhook handlers keyed by Stripe event type.

    The billing split: the app registers handlers that mutate its
    own domain models against the platform/connect registries below; the platform
    owns the signature verification + dispatch and names no event types or
    models itself.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[WebhookHandler]] = {}

    def register(self, event_type: str, handler: WebhookHandler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def handler(self, *event_types: str) -> Callable[[WebhookHandler], WebhookHandler]:
        def decorator(func: WebhookHandler) -> WebhookHandler:
            for event_type in event_types:
                self.register(event_type, func)
            return func

        return decorator

    async def dispatch(self, event: stripe.Event, transaction: AsyncSession) -> None:
        event_type: str = event["type"]
        handlers = self._handlers.get(event_type)
        if not handlers:
            logger.debug("Unhandled webhook event: %s", event_type)
            return
        for handler in handlers:
            await handler(event, transaction)


# Two Stripe channels → two registries: platform billing and Connect.
platform_webhook_registry = BillingWebhookRegistry()
connect_webhook_registry = BillingWebhookRegistry()


async def _verify_stripe_signature(request: Request, secret: str) -> stripe.Event:
    """Verify Stripe-Signature header and return the parsed event."""
    sig = request.headers.get("Stripe-Signature")
    if not sig:
        raise NotAuthorizedException("Missing Stripe-Signature header")
    body = await request.body()
    try:
        return stripe.Webhook.construct_event(body, sig, secret)
    except stripe.SignatureVerificationError as exc:
        raise NotAuthorizedException("Invalid Stripe signature") from exc


async def _parse_event(request: Request, secret: str) -> stripe.Event:
    # Skip signature verification in dev/test when the secret is not configured.
    if secret:
        return await _verify_stripe_signature(request, secret)
    body = await request.json()
    return stripe.Event.construct_from(body, key=None)  # type: ignore[arg-type]


def build_billing_webhook_router(
    *,
    path: str = "/",
    platform_registry: BillingWebhookRegistry = platform_webhook_registry,
    connect_registry: BillingWebhookRegistry = connect_webhook_registry,
) -> Router:
    @post("/webhooks/billing/stripe", exclude_from_auth=True)
    async def handle_platform_webhook(
        request: Request,
        transaction: AsyncSession,
    ) -> dict[str, str]:
        """Platform Stripe webhook — subscription lifecycle events."""
        event = await _parse_event(request, config.STRIPE_WEBHOOK_SECRET)
        await platform_registry.dispatch(event, transaction)
        return {"status": "ok"}

    @post("/webhooks/billing/stripe/connect", exclude_from_auth=True)
    async def handle_connect_webhook(
        request: Request,
        transaction: AsyncSession,
    ) -> dict[str, str]:
        """Stripe Connect webhook — account and payment events."""
        event = await _parse_event(request, config.STRIPE_CONNECT_WEBHOOK_SECRET)
        await connect_registry.dispatch(event, transaction)
        return {"status": "ok"}

    return Router(
        path=path,
        route_handlers=[handle_platform_webhook, handle_connect_webhook],
    )
