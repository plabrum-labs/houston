"""Wire types for the App read endpoints.

List/detail outputs inherit `ActionableList`/`ActionableDetail`, so the `actions`
field is part of every resource's read contract — CRUD hydrates it at request time
when `action_deps` is available.
"""

from app.platform.actions.schemas import ActionableDetail, ActionableList
from app.platform.utils.sqids import Sqid


class AppListItem(ActionableList):
    id: Sqid
    name: str
    repo_url: str
    state: str


class AppDetail(ActionableDetail):
    id: Sqid
    name: str
    repo_url: str
    state: str
