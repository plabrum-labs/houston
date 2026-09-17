"""Per-FieldType validation for FormNode values.

`UpdateNodeValue` calls `validate_field_value(config, value)` where `config`
is the FieldDef snapshot stored on the node. Returns the value coerced into
its canonical storage form, or raises `ValidationException`.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import msgspec
from litestar.exceptions import ValidationException

from app.platform.form_dsl.schema import FieldDef, FieldType


def validate_field_value(config: dict[str, Any] | None, value: Any) -> Any:
    if config is None:
        raise ValidationException("Node has no field config; cannot validate value")

    field = msgspec.convert(config, FieldDef)

    if value is None:
        if field.required:
            raise ValidationException(f"Field '{field.label}' is required")
        return None

    options = field.config.get("options") or []

    match field.type:
        case FieldType.TEXT | FieldType.LONGTEXT:
            _expect(isinstance(value, str), field, "string")
            return value

        case FieldType.NUMBER | FieldType.CURRENCY:
            # Booleans are instances of int in Python — reject explicitly.
            _expect(isinstance(value, (int, float)) and not isinstance(value, bool), field, "number")
            return value

        case FieldType.BOOLEAN:
            _expect(isinstance(value, bool), field, "boolean")
            return value

        case FieldType.SELECT | FieldType.SEGMENTED:
            _expect(isinstance(value, str), field, "string")
            if options and value not in options:
                raise ValidationException(f"'{value}' is not a valid option for {field.label}")
            return value

        case FieldType.MULTISELECT:
            _expect(isinstance(value, list) and all(isinstance(v, str) for v in value), field, "list of strings")
            if options:
                bad = [v for v in value if v not in options]
                if bad:
                    raise ValidationException(f"Invalid options for {field.label}: {bad}")
            return value

        case FieldType.DATE:
            _expect(isinstance(value, str), field, "ISO date string")
            try:
                date.fromisoformat(value)
            except ValueError as err:
                raise ValidationException(f"Invalid date for {field.label}: {value}") from err
            return value

        case FieldType.PHOTO:
            _expect(isinstance(value, list) and all(isinstance(v, str) for v in value), field, "list of media ids")
            return value

        case FieldType.REPEATER:
            # Repeater node values are managed via AddRepeaterInstance, not
            # UpdateNodeValue. Caller shouldn't be writing through here.
            raise ValidationException("Repeater values are managed via repeater instance nodes")

        case FieldType.TABLE | FieldType.SIGNATURE | FieldType.ANNOTATED_IMAGE:
            _expect(isinstance(value, dict), field, "object")
            return value

        case FieldType.STATIC_TEXT:
            raise ValidationException(f"Field '{field.label}' is static text and cannot be edited")

        case FieldType.GROUP:
            raise ValidationException(f"Field '{field.label}' is a group and carries no value of its own")


def _expect(ok: bool, field: FieldDef, expected: str) -> None:
    if not ok:
        raise ValidationException(f"Field '{field.label}' expects {expected}")
