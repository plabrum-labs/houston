"""Higher-level billing operations wrapping the Stripe client."""

from datetime import datetime

from app.platform.billing.client import BaseBillingClient


class BillingService:
    def __init__(self, client: BaseBillingClient) -> None:
        self._client = client

    # ─── SaaS billing ─────────────────────────────────────────────────────────

    async def create_customer(self, name: str, email: str) -> str:
        """Create a Stripe customer for an org. Returns stripe_customer_id."""
        return await self._client.create_customer(name=name, email=email)

    async def create_subscription(
        self, customer_id: str, price_id: str
    ) -> tuple[str, datetime | None, datetime | None]:
        """Create a subscription. Returns (stripe_subscription_id, period_start, period_end)."""
        return await self._client.create_subscription(customer_id=customer_id, price_id=price_id)

    async def update_subscription(self, subscription_id: str, price_id: str) -> None:
        """Swap the price on an existing subscription."""
        await self._client.update_subscription(subscription_id=subscription_id, price_id=price_id)

    async def cancel_subscription(self, subscription_id: str) -> None:
        """Schedule a subscription for cancellation at period end."""
        await self._client.cancel_subscription(subscription_id=subscription_id)

    # ─── Connect ──────────────────────────────────────────────────────────────

    async def create_connected_account(self, name: str, email: str) -> str:
        """Create a Stripe Connect account for an org. Returns stripe_account_id."""
        return await self._client.create_account(name=name, email=email)

    async def create_account_link(self, stripe_account_id: str, return_url: str, refresh_url: str) -> str:
        """Generate a Connect onboarding URL."""
        return await self._client.create_account_link(
            account_id=stripe_account_id,
            return_url=return_url,
            refresh_url=refresh_url,
        )

    async def retrieve_connected_account(self, stripe_account_id: str) -> dict:
        """Retrieve the full Stripe account object."""
        return await self._client.retrieve_account(account_id=stripe_account_id)

    async def update_connected_account(self, stripe_account_id: str, fields: dict) -> dict:
        """Update fields on a Connect account. `fields` is passed through to Stripe."""
        return await self._client.update_account(account_id=stripe_account_id, fields=fields)

    async def accept_tos(self, account_id: str, ip: str, user_agent: str) -> None:
        """Record TOS acceptance for a Connect account."""
        await self._client.accept_tos(account_id=account_id, ip=ip, user_agent=user_agent)

    async def attach_external_account(self, account_id: str, token: str) -> dict:
        """Attach a bank account or debit card to a Connect account for payouts."""
        return await self._client.attach_external_account(account_id=account_id, token=token)

    async def create_setup_intent(self, customer_id: str) -> str:
        """Create a SetupIntent for saving a payment method. Returns client_secret."""
        return await self._client.create_setup_intent(customer_id=customer_id)

    async def retrieve_payment_method(self, payment_method_id: str) -> dict:
        """Retrieve card details for a payment method."""
        return await self._client.retrieve_payment_method(payment_method_id=payment_method_id)

    async def set_default_payment_method(self, customer_id: str, payment_method_id: str) -> None:
        """Set the default payment method on a Stripe customer."""
        await self._client.set_default_payment_method(customer_id=customer_id, payment_method_id=payment_method_id)

    async def detach_payment_method(self, payment_method_id: str) -> None:
        """Detach a payment method from its customer."""
        await self._client.detach_payment_method(payment_method_id=payment_method_id)

    async def create_payment_intent(
        self, amount_cents: int, currency: str, connected_account_id: str, invoice_id: str
    ) -> tuple[str, str]:
        """Create a destination-charge PaymentIntent. Returns (payment_intent_id, client_secret)."""
        return await self._client.create_payment_intent(
            amount_cents=amount_cents,
            currency=currency,
            connected_account_id=connected_account_id,
            invoice_id=invoice_id,
        )

    async def refund_payment_intent(self, payment_intent_id: str, connected_account_id: str) -> str:
        """Refund a destination-charge PaymentIntent. Returns the refund ID."""
        return await self._client.refund_payment_intent(
            payment_intent_id=payment_intent_id,
            connected_account_id=connected_account_id,
        )

    async def cancel_payment_intent(self, payment_intent_id: str) -> None:
        """Cancel a PaymentIntent that has not yet succeeded."""
        await self._client.cancel_payment_intent(payment_intent_id=payment_intent_id)

    async def upload_identity_document(
        self, account_id: str, file_content: bytes, filename: str, content_type: str
    ) -> str:
        """Upload an identity document to a Connect account. Returns the Stripe file ID."""
        return await self._client.upload_identity_document(
            account_id=account_id,
            file_content=file_content,
            filename=filename,
            content_type=content_type,
        )
