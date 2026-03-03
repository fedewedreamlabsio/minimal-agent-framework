from __future__ import annotations

from typing import Any

from .contracts import JsonDict


def validate_json(value: Any, schema: JsonDict, path: str = "$") -> list[str]:
    if not schema:
        return []

    errors: list[str] = []

    one_of = schema.get("oneOf")
    if isinstance(one_of, list) and one_of:
        variant_errors = [validate_json(value, variant, path) for variant in one_of]
        if not any(len(item) == 0 for item in variant_errors):
            errors.append(f"{path}: did not match any oneOf schema")
        return errors

    expected_type = schema.get("type")
    if expected_type is not None:
        if not _is_type_match(value, expected_type):
            errors.append(
                f"{path}: expected type {expected_type!r}, got {type(value).__name__!r}"
            )
            return errors

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} not in enum {schema['enum']!r}")

    if expected_type == "object" and isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required key {key!r}")

        properties = schema.get("properties", {})
        additional_properties = schema.get("additionalProperties", True)
        for key, sub_value in value.items():
            if key in properties:
                errors.extend(validate_json(sub_value, properties[key], f"{path}.{key}"))
            elif additional_properties is False:
                errors.append(f"{path}: unexpected key {key!r}")

    if expected_type == "array" and isinstance(value, list):
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(validate_json(item, item_schema, f"{path}[{index}]"))

    return errors


def _is_type_match(value: Any, expected_type: Any) -> bool:
    if isinstance(expected_type, list):
        return any(_is_type_match(value, member) for member in expected_type)

    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return (isinstance(value, int) and not isinstance(value, bool)) or isinstance(value, float)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "null":
        return value is None
    return True
