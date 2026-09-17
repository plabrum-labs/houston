from enum import Enum


class FormNodeKind(Enum):
    section = "section"
    field = "field"
    repeater_instance = "repeater_instance"
    # Domain-specific sub-entry (e.g. a checklist finding). Owners interpret the
    # `value` payload; the platform treats it as an opaque tree node.
    annotation = "annotation"
