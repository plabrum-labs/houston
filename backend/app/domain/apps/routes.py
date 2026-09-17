"""CRUD read endpoints for App — the read pillar from an app's view.

`CRUDConfig` + `make_crud_controller` give POST / (list/filter/sort/search) and
GET /{id} (detail). Writes live in `actions.py`. The transformer callables own the
wire shape.
"""

from typing import Any

from app.domain.apps.models import App
from app.domain.apps.schemas import AppDetail, AppListItem
from app.platform.base.crud import CRUDConfig, make_crud_controller
from app.platform.data.enums import FieldType
from app.platform.data.service import FieldConfig
from app.platform.state_machine.roles import Actor


def _to_list_item(obj: App, user: Actor[Any]) -> AppListItem:
    return AppListItem(id=obj.id, name=obj.name, repo_url=obj.repo_url, state=obj.state.value)


def _to_detail(obj: App, user: Actor[Any]) -> AppDetail:
    return AppDetail(id=obj.id, name=obj.name, repo_url=obj.repo_url, state=obj.state.value)


app_crud_config = CRUDConfig(
    model=App,
    to_list_item=_to_list_item,
    to_detail=_to_detail,
    filterable_columns={"name", "state"},
    sortable_columns={"name", "created_at"},
    data_fields=[FieldConfig(name="state", label="State", field_type=FieldType.ENUM)],
)


def build_apps_controller(base_guards: list[Any]) -> type:
    return make_crud_controller("/apps", app_crud_config, base_guards=base_guards)
