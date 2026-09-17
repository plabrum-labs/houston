import inspect
import sys
import types
from datetime import date, datetime
from enum import Enum
from functools import reduce
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    TypeAliasType,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

import msgspec

from app.platform.actions.enums import ActionResultType
from app.platform.base.schemas import BaseSchema
from app.platform.utils.sqids import Sqid

if TYPE_CHECKING:
    from app.platform.actions.registry import ActionRegistry


# Populated by build_action_metadata() in routes.py — exposed via GET /schema/action-metadata.
_action_metadata: dict[str, dict] = {}


class ActionCTA(BaseSchema):
    label: str
    path: str


class DisabledReason(BaseSchema):
    message: str
    cta: ActionCTA | None = None


class ActionDTO(BaseSchema):
    action: str
    label: str
    action_group_type: str
    is_bulk_allowed: bool = False
    available: bool = True
    priority: int = 100
    icon: str | None = None
    confirmation_message: str | None = None
    should_redirect_to_parent: bool = False
    disabled_reason: DisabledReason | None = None
    # When set, the action transitions its object to this state value.
    # Frontends derive `is_state_transition` as `target_state is not None`.
    target_state: str | None = None


class ActionExecutionRequest(BaseSchema):
    action_group: str
    object_id: Sqid


class RedirectActionResult(BaseSchema, tag=ActionResultType.REDIRECT.value):
    path: str  # e.g., "/brands/123" or ".." for parent


class DownloadFileActionResult(BaseSchema, tag=ActionResultType.DOWNLOAD_FILE.value):
    url: str
    filename: str


class CopyToClipboardActionResult(BaseSchema, tag=ActionResultType.COPY_TO_CLIPBOARD.value):
    text: str
    toast: str | None = None


ActionResult = RedirectActionResult | DownloadFileActionResult | CopyToClipboardActionResult


class ActionExecutionResponse(BaseSchema):
    """Response from action execution with metadata for navigation and query invalidation."""

    message: str = ""
    invalidate_queries: list[str] = []  # Query keys to invalidate
    action_result: ActionResult | None = None  # Frontend action to perform
    created_id: Sqid | None = None  # ID of newly created object (for create actions)


class ActionListResponse(BaseSchema):
    actions: list[ActionDTO]


# CRUD list and detail schemas inherit from these so the `actions` field is part
# of every resource's read contract — the CRUD layer hydrates it at request time.
# `kw_only=True` lets subclasses declare required fields without ordering issues.
class Actionable(BaseSchema, kw_only=True):
    actions: list[ActionDTO] = []


class ActionableList(Actionable):
    pass


class ActionableDetail(Actionable):
    pass


# --- Helper functions for Action union generation -------------------------------


def _base_type(tp: Any) -> Any:
    """Extract base type from Annotated types."""
    return get_args(tp)[0] if get_origin(tp) is Annotated else tp


def default_tp(tp: Any | None) -> list[tuple[str, Any]]:
    """Return struct field definitions for the provided type."""
    if tp is None or tp is inspect._empty:
        return []
    if isinstance(tp, TypeAliasType):
        tp = getattr(tp, "__value__", tp)
    return [("data", tp)]


def _extract_data_param_type(action_cls: type) -> Any | None:
    """Extract the type annotation of the 'data' parameter from an action's execute method."""
    meth = getattr(action_cls, "execute")
    fn = meth.__func__ if isinstance(meth, classmethod | staticmethod) else meth
    fn = inspect.unwrap(fn)

    sig = inspect.signature(fn)
    if "data" not in sig.parameters:
        return None

    mod = sys.modules.get(action_cls.__module__)
    hints = get_type_hints(
        fn,
        globalns=getattr(mod, "__dict__", {}),
        localns=vars(action_cls),
        include_extras=True,
    )
    ann = hints.get("data", sig.parameters["data"].annotation)
    if ann is inspect._empty:
        raise TypeError(f"{action_cls.__name__}.execute 'data' is unannotated")
    return _base_type(ann)


def build_action_metadata(action_registry: "ActionRegistry") -> dict[str, dict]:
    """Build form metadata for all registered actions.

    Exposed via GET /schema/action-metadata for frontend form codegen.
    """
    metadata: dict[str, dict] = {}

    for action_key, action_cls in action_registry._flat_registry.items():
        tp = _extract_data_param_type(action_cls)

        # No data param or EmptyActionData → no form
        if tp is None or getattr(tp, "__name__", "") == "EmptyActionData":
            metadata[action_key] = {
                "has_form": False,
                "label": action_cls.label,
                "is_hidden": action_cls.is_hidden,
            }
            continue

        # Introspect struct fields
        fields_info = msgspec.structs.fields(tp)
        schema_name = tp.__name__

        id_fields_from_class: set[str] = getattr(action_cls, "form_id_fields", set())
        entity_fields: dict[str, dict] = getattr(action_cls, "form_entity_fields", {})
        field_order: list[str] = getattr(action_cls, "form_field_order", [])
        field_labels: dict[str, str] = getattr(action_cls, "form_field_labels", {})
        field_placeholders: dict[str, str] = getattr(action_cls, "form_field_placeholders", {})

        fields_by_name = {fi.name: fi for fi in fields_info}
        all_sqid = not entity_fields  # entity_ref fields are never plain Sqid
        field_meta: dict[str, dict] = {}

        # Entity ref fields: declared on the action class, no type introspection needed
        for field_name, spec in entity_fields.items():
            fi = fields_by_name.get(field_name)
            idx = list(fields_by_name).index(field_name) if field_name in fields_by_name else 999
            order = field_order.index(field_name) if field_name in field_order else (len(field_order) + idx)
            entry: dict[str, Any] = {
                "required": fi.required if fi else False,
                "order": order,
                "type": "entity_ref",
                "model": spec["model"],
                "create_action": spec.get("create_action"),
                "is_id_field": False,
            }
            if field_name in field_labels:
                entry["label"] = field_labels[field_name]
            if field_name in field_placeholders:
                entry["placeholder"] = field_placeholders[field_name]
            field_meta[field_name] = entry

        # Remaining struct fields: detect type from annotation
        for idx, fi in enumerate(fields_info):
            if fi.name in entity_fields:
                continue

            raw_type = fi.type
            origin = get_origin(raw_type)
            type_args = get_args(raw_type) if origin else ()

            # Unwrap X | None → X (handles both types.UnionType and typing.Union/Optional)
            base = raw_type
            if origin is types.UnionType or origin is Union:
                non_none = [a for a in type_args if a is not type(None)]
                base = non_none[0] if len(non_none) == 1 else raw_type

            order = field_order.index(fi.name) if fi.name in field_order else (len(field_order) + idx)

            entry = {
                "required": fi.required,
                "order": order,
            }
            if fi.name in field_labels:
                entry["label"] = field_labels[fi.name]
            if fi.name in field_placeholders:
                entry["placeholder"] = field_placeholders[fi.name]

            is_sqid = base is Sqid
            if not is_sqid:
                all_sqid = False

            is_id_field = is_sqid or fi.name in id_fields_from_class

            field_type = "string"
            if base is bool:
                field_type = "boolean"
            elif base is int or base is float:
                field_type = "number"
                # `*_cents` integer/float fields are money. Tag them so the form
                # codegen emits a dollars-in/cents-out input and a label without
                # the misleading "Cents" suffix.
                if fi.name.endswith("_cents"):
                    field_type = "currency"
                    if "label" not in entry:
                        stripped = fi.name.removesuffix("_cents").replace("_", " ").title()
                        entry["label"] = stripped or "Amount"
            elif base is date:
                field_type = "date"
            elif base is datetime:
                field_type = "datetime"
            elif isinstance(base, type) and issubclass(base, Enum):
                field_type = "enum"
            elif is_sqid:
                field_type = "id"

            entry["type"] = field_type
            if is_id_field:
                entry["is_id_field"] = True

            field_meta[fi.name] = entry

        has_form = not all_sqid and not action_cls.is_hidden

        metadata[action_key] = {
            "schema_name": schema_name,
            "has_form": has_form,
            "label": action_cls.label,
            "is_hidden": action_cls.is_hidden,
            "fields": field_meta,
        }

    return metadata


def build_action_union(action_registry: "ActionRegistry") -> TypeAliasType:
    """Build a discriminated union type from all registered actions.

    Iterates through all registered actions, extracts their data parameter types,
    and creates a discriminated union with tag-based discrimination using the action key.
    """
    action_structs: list[type[msgspec.Struct]] = []

    for action_key, action_cls in action_registry._flat_registry.items():
        tp = _extract_data_param_type(action_cls)
        fields = default_tp(tp)

        struct_class = msgspec.defstruct(
            f"{action_cls.__name__}Action",
            fields,
            tag_field="action",
            tag=action_key,
        )
        action_structs.append(struct_class)

        action_registry._struct_to_action[struct_class] = action_cls

    _action_union = (
        reduce(lambda a, b: a | b, action_structs) if action_structs else msgspec.Struct  # type: ignore[arg-type, return-value]
    )
    return TypeAliasType("Action", _action_union)  # type: ignore[valid-type]
