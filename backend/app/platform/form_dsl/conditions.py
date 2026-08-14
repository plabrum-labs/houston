"""Condition resolver + per-section completion projection over `form_nodes`.

The template's `FieldCondition` references a field by `schema_ref` (template
id) and asserts an `equals` value. We resolve against the materialized node
tree: a section/field with a condition that doesn't match is "skipped" and
should render as a placeholder rather than collect a value.
"""

from __future__ import annotations

from collections.abc import Iterable

import msgspec

from app.platform.form_dsl.enums import FormNodeKind
from app.platform.form_dsl.models import FormNode
from app.platform.form_dsl.schema import FieldCondition, FieldType


def _condition_for(node: FormNode) -> FieldCondition | None:
    if not node.config:
        return None
    raw = node.config.get("condition") if node.kind == FormNodeKind.section else None
    if raw is None and node.kind == FormNodeKind.field:
        # Field config is a FieldDef dump; condition lives at top level.
        raw = node.config.get("condition")
    if raw is None:
        return None
    return msgspec.convert(raw, FieldCondition)


def resolve_visibility(nodes: Iterable[FormNode]) -> dict[int, bool]:
    """Return `{node_id: visible}` for every node that carries a condition.

    Nodes without a condition are omitted (caller treats absence as visible).
    """
    by_schema_ref: dict[str, FormNode] = {
        n.schema_ref: n for n in nodes if n.kind == FormNodeKind.field and n.schema_ref is not None
    }

    visibility: dict[int, bool] = {}
    for node in nodes:
        condition = _condition_for(node)
        if condition is None:
            continue
        source = by_schema_ref.get(condition.field)
        if source is None:
            visibility[node.id] = False
            continue
        visibility[node.id] = source.value == condition.equals
    return visibility


def section_completion(nodes: Iterable[FormNode]) -> dict[int, dict[str, int]]:
    """Per-section `{filled, total}` counts.

    A field counts toward `total` if it is visible (no condition, or condition
    resolves true) and not static text or a group (groups carry no value of
    their own — see validate.py). It counts toward `filled` if `value` is
    non-null.
    """
    nodes = list(nodes)
    visibility = resolve_visibility(nodes)

    # Map every field node up to its enclosing top-level section.
    section_id_by_node: dict[int, int] = {}
    by_id = {n.id: n for n in nodes}
    for n in nodes:
        cur = n
        while cur.parent_id is not None and cur.parent_id in by_id:
            cur = by_id[cur.parent_id]
        if cur.kind == FormNodeKind.section:
            section_id_by_node[n.id] = cur.id

    counts: dict[int, dict[str, int]] = {}
    for n in nodes:
        if n.kind != FormNodeKind.field:
            continue
        section_id = section_id_by_node.get(n.id)
        if section_id is None:
            continue
        # Skip when the field or its enclosing section is hidden.
        if visibility.get(section_id, True) is False:
            continue
        if visibility.get(n.id, True) is False:
            continue
        if n.config and n.config.get("type") in (FieldType.STATIC_TEXT.value, FieldType.GROUP.value):
            continue
        bucket = counts.setdefault(section_id, {"filled": 0, "total": 0})
        bucket["total"] += 1
        if n.value is not None:
            bucket["filled"] += 1
    return counts
