from __future__ import annotations

from typing import Any

from app.platform.base.schemas import BaseSchema
from app.platform.form_dsl.enums import FormNodeKind
from app.platform.form_dsl.schema import FieldType
from app.platform.utils.sqids import Sqid


class FormNodeRef(BaseSchema):
    """Flat node projection. Callers reconstruct the tree by `parent_id`."""

    id: Sqid
    parent_id: Sqid | None
    kind: FormNodeKind
    schema_ref: str | None
    label: str
    value: Any | None
    config: dict[str, Any] | None
    sort_order: int
    # None when no condition applies; True/False once resolved.
    condition_visible: bool | None = None


class SectionCompletion(BaseSchema):
    section_id: Sqid
    filled: int
    total: int


class UpdateNodeValueData(BaseSchema):
    value: Any | None


class AddRepeaterInstanceData(BaseSchema):
    repeater_node_id: Sqid


class AddAdHocFieldData(BaseSchema):
    parent_id: Sqid  # section, group field, or repeater instance node
    label: str
    type: FieldType
    options: list[str] = []
    required: bool = False


class AddAdHocSectionData(BaseSchema):
    owner_type: str
    owner_id: Sqid
    title: str
