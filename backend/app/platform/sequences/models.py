from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.base.models import BaseDBModel
from app.platform.base.rls_mixins import OrgScopedMixin


class BusinessSequence(OrgScopedMixin, BaseDBModel):
    __tablename__ = "business_sequences"
    __table_args__ = (sa.UniqueConstraint("organization_id", "type", name="uq_business_sequences_org_type"),)

    organization_id: Mapped[int] = mapped_column(
        sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # `type` is the string key of the app's own SequenceType enum (stored as
    # `.name`). Demoted from `TextEnum(SequenceType)` to plain `str`: sequence-type
    # values are domain-specific (invoice/quote/order/…), so this shared table is
    # string-keyed and the app keeps its own enum — the platform never names a value.
    type: Mapped[str] = mapped_column(sa.Text, nullable=False)
    current_value: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
