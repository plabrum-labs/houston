from __future__ import annotations

from enum import StrEnum, auto
from typing import Any

from app.platform.base.schemas import BaseSchema


class FieldType(StrEnum):
    TEXT = auto()
    LONGTEXT = auto()
    SELECT = auto()
    MULTISELECT = auto()
    SEGMENTED = auto()
    NUMBER = auto()
    CURRENCY = auto()
    DATE = auto()
    BOOLEAN = auto()
    PHOTO = auto()
    TABLE = auto()
    REPEATER = auto()
    STATIC_TEXT = auto()
    SIGNATURE = auto()
    ANNOTATED_IMAGE = auto()
    GROUP = auto()


class FieldCondition(BaseSchema):
    field: str
    equals: Any


class FieldDef(BaseSchema):
    id: str
    label: str
    type: FieldType
    required: bool = False
    allow_finding: bool = True
    config: dict[str, Any] = {}
    condition: FieldCondition | None = None
    # Shared by GROUP (child fields of the group) and REPEATER (sub-fields defining each instance's shape).
    fields: list[FieldDef] = []
    min: int | None = None
    max: int | None = None
    instance_label_field: str | None = None


class Section(BaseSchema):
    id: str
    title: str
    condition: FieldCondition | None = None
    fields: list[FieldDef] = []


class TemplateDefinition(BaseSchema):
    version: int = 1
    sections: list[Section] = []
