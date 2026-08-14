"""Live Stripe billing client — the only module in `billing` that needs `stripe`
installed. Import this directly (not via `billing/__init__.py`) when you want
the real client; `billing/deps.py` imports it lazily inside the provider
function so a `Local*`-only app never needs the SDK.
"""

from datetime import UTC, datetime

import stripe

from app.config import Config
from app.platform.billing.client import BaseBillingClient


class StripeBillingClient(BaseBillingClient):
    """Live Stripe API client."""

    def __init__(self, config: Config) -> None:
        stripe.api_key = config.STRIPE_SECRET_KEY
        self._frontend_origin = config.FRONTEND_ORIGIN

    async def create_customer(self, name: str, email: str) -> str:
        customer = await stripe.Customer.create_async(name=name, email=email)
        return customer.id

    async def create_subscription(
        self, customer_id: str, price_id: str
    ) -> tuple[str, datetime | None, datetime | None]:
        sub = await stripe.Subscription.create_async(
            customer=customer_id,
            items=[{"price": price_id}],
        )
        # Period dates are populated by the customer.subscription.updated webhook.
        return sub.id, None, None

    async def update_subscription(self, subscription_id: str, price_id: str) -> None:
        sub = await stripe.Subscription.retrieve_async(subscription_id)
        item_id = sub.items.data[0].id
        await stripe.Subscription.modify_async(
            subscription_id,
            items=[{"id": item_id, "price": price_id}],
        )

    async def cancel_subscription(self, subscription_id: str) -> None:
        await stripe.Subscription.modify_async(subscription_id, cancel_at_period_end=True)

    async def create_account(self, name: str, email: str) -> str:
        # Use explicit controller properties — NOT the legacy type='custom'/'express'/'standard'.
        # Migrate to POST /v2/core/accounts once the Python SDK fully exposes it.
        account = await stripe.Account.create_async(
            email=email,
            business_profile={"name": name},
            controller={
                "losses": {"payments": "application"},
                "fees": {"payer": "application"},
                "stripe_dashboard": {"type": "express"},
                "requirement_collection": "application",
            },
            capabilities={
                "card_payments": {"requested": True},
                "transfers": {"requested": True},
            },
        )
        return account.id

    async def create_account_link(self, account_id: str, return_url: str, refresh_url: str) -> str:
        link = await stripe.AccountLink.create_async(
            account=account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            type="account_onboarding",
        )
        return link.url

    async def retrieve_account(self, account_id: str) -> dict:
        account = await stripe.Account.retrieve_async(account_id)
        return account.to_dict()

    async def update_account(self, account_id: str, fields: dict) -> dict:
        account = await stripe.Account.modify_async(account_id, **fields)
        return account.to_dict()

    async def accept_tos(self, account_id: str, ip: str, user_agent: str) -> None:
        now_unix = int(datetime.now(tz=UTC).timestamp())
        await stripe.Account.modify_async(
            account_id,
            tos_acceptance={"date": now_unix, "ip": ip, "user_agent": user_agent},
        )

    async def attach_external_account(self, account_id: str, token: str) -> dict:
        external_account = await stripe.Account.create_external_account_async(
            account_id,
            external_account=token,
        )
        return external_account.to_dict()

    async def create_setup_intent(self, customer_id: str) -> str:
        si = await stripe.SetupIntent.create_async(
            customer=customer_id,
            payment_method_types=["card"],
        )
        assert si.client_secret is not None
        return si.client_secret

    async def retrieve_payment_method(self, payment_method_id: str) -> dict:
        pm = await stripe.PaymentMethod.retrieve_async(payment_method_id)
        card = pm.card
        return {
            "brand": getattr(card, "brand", "") or "",
            "last4": getattr(card, "last4", "") or "",
            "exp_month": getattr(card, "exp_month", 0) or 0,
            "exp_year": getattr(card, "exp_year", 0) or 0,
        }

    async def set_default_payment_method(self, customer_id: str, payment_method_id: str) -> None:
        await stripe.Customer.modify_async(
            customer_id,
            invoice_settings={"default_payment_method": payment_method_id},
        )

    async def detach_payment_method(self, payment_method_id: str) -> None:
        await stripe.PaymentMethod.detach_async(payment_method_id)

    async def create_payment_intent(
        self, amount_cents: int, currency: str, connected_account_id: str, invoice_id: str
    ) -> tuple[str, str]:
        pi = await stripe.PaymentIntent.create_async(
            amount=amount_cents,
            currency=currency.lower(),
            transfer_data={"destination": connected_account_id},
            metadata={"invoice_id": invoice_id},
        )
        assert pi.client_secret is not None
        return pi.id, pi.client_secret

    async def refund_payment_intent(self, payment_intent_id: str, connected_account_id: str) -> str:
        refund = await stripe.Refund.create_async(
            payment_intent=payment_intent_id,
            reverse_transfer=True,
        )
        return refund.id

    async def cancel_payment_intent(self, payment_intent_id: str) -> None:
        await stripe.PaymentIntent.cancel_async(payment_intent_id)

    async def upload_identity_document(
        self, account_id: str, file_content: bytes, filename: str, content_type: str
    ) -> str:
        f = await stripe.File.create_async(
            purpose="identity_document",
            file=(filename, file_content, content_type),
            stripe_account=account_id,
        )
        return f.id
