from __future__ import annotations

from typing import Any

from app.platform.base.schemas import BaseSchema


class ConnectAddressInput(BaseSchema):
    line1: str | None
    line2: str | None
    city: str | None
    state: str | None
    postal_code: str | None
    country: str | None


class ConnectDOBInput(BaseSchema):
    day: int
    month: int
    year: int


class ConnectIndividualInput(BaseSchema):
    first_name: str | None
    last_name: str | None
    email: str | None
    phone: str | None
    address: ConnectAddressInput | None
    dob: ConnectDOBInput | None
    ssn_last_4: str | None


class ConnectCompanyInput(BaseSchema):
    name: str | None
    phone: str | None
    address: ConnectAddressInput | None


class ConnectBusinessProfileInput(BaseSchema):
    mcc: str | None
    url: str | None
    product_description: str | None


class UpdateConnectAccountData(BaseSchema):
    business_type: str | None
    individual: ConnectIndividualInput | None
    company: ConnectCompanyInput | None
    business_profile: ConnectBusinessProfileInput | None


class ConnectAccountResponse(BaseSchema):
    stripe_account_id: str


class AcceptTosData(BaseSchema):
    ip: str
    user_agent: str


class AttachExternalAccountData(BaseSchema):
    token: str


class ExternalAccountResponse(BaseSchema):
    last4: str
    bank_name: str | None
    routing_number: str | None


class ConnectAccountRequirementsBlock(BaseSchema):
    currently_due: list[str]
    eventually_due: list[str]
    pending_verification: list[str]


class ConnectAccountRequirementsResponse(BaseSchema):
    currently_due: list[str]
    eventually_due: list[str]
    pending_verification: list[str]
    future_requirements: dict[str, Any]
    charges_enabled: bool
    payouts_enabled: bool


class ConnectAccountStatusResponse(BaseSchema):
    stripe_account_id: str
    charges_enabled: bool
    payouts_enabled: bool
    requirements: dict[str, Any]


class IdentityDocumentResponse(BaseSchema):
    file_id: str
