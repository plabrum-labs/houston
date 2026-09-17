from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.base.models import BaseDBModel
from app.platform.base.rls_mixins import OrgScopedMixin
from app.platform.form_dsl.enums import FormNodeKind
from app.platform.utils.sqids import Sqid, SqidType
from app.platform.utils.textenum import TextEnum


class FormNode(OrgScopedMixin, BaseDBModel):
    """One row per addressable thing in a form response: section, field
    (including group fields), repeater instance, or domain-specific annotation.

    Owned polymorphically by any model that materializes a `TemplateDefinition`
    — keyed by `(owner_type, owner_id)` where `owner_type` is the owner's
    table name (mirrors the threadable pattern).
    """

    __tablename__ = "form_nodes"
    __table_args__ = (sa.Index("ix_form_nodes_owner", "owner_type", "owner_id"),)

    organization_id: Mapped[int] = mapped_column(
        sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    owner_type: Mapped[str] = mapped_column(sa.Text, nullable=False)
    owner_id: Mapped[Sqid] = mapped_column(SqidType, nullable=False)
    parent_id: Mapped[Sqid | None] = mapped_column(
        SqidType, sa.ForeignKey("form_nodes.id", ondelete="CASCADE"), nullable=True, index=True
    )
    kind: Mapped[FormNodeKind] = mapped_column(TextEnum(FormNodeKind), nullable=False)
    # Template node id this row was materialized from; null for ad-hoc nodes
    # and annotations.
    schema_ref: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    label: Mapped[str] = mapped_column(sa.Text, nullable=False)
    value: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # Snapshot of the field-type config so the response renders correctly even
    # if the template node is later renamed or deleted.
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    sort_order: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0, server_default="0")
