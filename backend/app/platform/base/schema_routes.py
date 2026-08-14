"""Codegen metadata router: crud-metadata + action-metadata.

The source app mounts this as a module-level `schema_router` guarded by
`requires_local`. The platform doesn't own that guard, so this is a factory — the app
injects its guards (D15 seam).
"""

from collections.abc import Sequence

from litestar import Router, get
from litestar.types import Guard

from app.platform.actions.registry import ActionRegistry
from app.platform.actions.schemas import _action_metadata
from app.platform.base.crud import CRUDRegistry, _crud_metadata
from app.platform.state_machine.models import get_state_machine_meta


def build_schema_router(*, path: str = "/schema", guards: Sequence[Guard] = ()) -> Router:
    """Build the codegen-metadata router for an app.

    Args:
        path: Mount path (default "/schema").
        guards: Litestar guards applied to every route (e.g. requires_local).
    """

    @get("/crud-metadata", tags=["schema"], exclude_from_auth=True)
    async def crud_metadata() -> dict:
        """Column metadata for frontend codegen.

        Includes filterable/sortable columns per CRUD resource, plus a
        `state_machine: {column, states, action_group}` block for any resource
        whose model uses `StateMachineMixin`. State-machine awareness is asserted
        by the backend (not inferred from column names) so the codegen can drop
        its name-based heuristics.
        """
        out: dict[str, dict] = {k: dict(v) for k, v in _crud_metadata.items()}
        for model in CRUDRegistry().get_all_types():
            sm = get_state_machine_meta(model)
            if sm is None:
                continue
            group = ActionRegistry().find_by_model(model)
            if group is not None:
                sm["action_group"] = group.group_type.value
            key = f"list_{model.__name__}"
            if key in out:
                out[key]["state_machine"] = sm
        return out

    @get("/action-metadata", tags=["schema"], exclude_from_auth=True)
    async def action_metadata() -> dict:
        """Action form metadata for frontend codegen (field types, labels, ordering per action)."""
        return _action_metadata

    return Router(
        path=path,
        route_handlers=[crud_metadata, action_metadata],
        tags=["schema"],
        guards=list(guards),
    )
