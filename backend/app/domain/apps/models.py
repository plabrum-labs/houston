"""The `App` domain entity — Houston's core noun.

An app is org-scoped, searchable, and driven by a state machine (registered →
provisioning → live ⇄ suspended). Org-scoped + searchable + state-machine-driven, it
exercises the whole platform spine.
"""

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.apps.enums import AppState
from app.platform.base.rls_mixins import OrgScopedMixin
from app.platform.base.search import SearchMixin
from app.platform.state_machine.models import StateMachineMixin


class App(
    OrgScopedMixin,
    SearchMixin,
    StateMachineMixin(state_enum=AppState, initial_state=AppState.registered),
):
    __tablename__ = "apps"

    # SearchMixin config — trigram search over the name.
    trgm_columns = ["name"]
    search_label_field = "name"
    search_entity_type = "app"
    search_detail_prefix = "APP"

    organization_id: Mapped[int] = mapped_column(sa.ForeignKey("organizations.id"))
    name: Mapped[str] = mapped_column(sa.Text)
    repo_url: Mapped[str] = mapped_column(sa.Text)
