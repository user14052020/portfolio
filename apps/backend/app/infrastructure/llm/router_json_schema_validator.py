from __future__ import annotations

from typing import Any

from app.application.stylist_chat.contracts.ports import (
    RouterSchemaValidationOutput,
    RouterSchemaValidatorPort,
)

from .router_response_schema import ROUTER_DECISION_JSON_SCHEMA


class RouterJsonSchemaValidator(RouterSchemaValidatorPort):
    def __init__(self, *, schema: dict[str, Any] | None = None) -> None:
        self.schema = schema or ROUTER_DECISION_JSON_SCHEMA
        self.properties = self.schema.get("properties", {})
        self.required = set(self.schema.get("required", []))

    def validate(self, *, payload: Any) -> RouterSchemaValidationOutput:
        if not isinstance(payload, dict):
            return RouterSchemaValidationOutput(errors=["router payload must be a JSON object"])

        normalized_payload = {
            key: value
            for key, value in payload.items()
            if key in self.properties
        }
        stripped_fields = [
            key
            for key in payload.keys()
            if key not in self.properties
        ]
        errors: list[str] = []

        for field_name in self.required:
            if field_name not in normalized_payload:
                errors.append(f"{field_name} is required")

        for field_name, value in normalized_payload.items():
            field_schema = self.properties.get(field_name, {})
            field_errors = self._validate_field(field_name=field_name, value=value, field_schema=field_schema)
            errors.extend(field_errors)

        return RouterSchemaValidationOutput(
            payload=normalized_payload,
            errors=errors,
            stripped_fields=stripped_fields,
        )

    def _validate_field(
        self,
        *,
        field_name: str,
        value: Any,
        field_schema: dict[str, Any],
    ) -> list[str]:
        expected_type = field_schema.get("type")
        if expected_type is None:
            return []

        if not self._matches_type(value=value, expected_type=expected_type):
            return [f"{field_name} has invalid type"]

        if "enum" in field_schema and value not in field_schema["enum"]:
            return [f"{field_name} is not in enum"]

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            minimum = field_schema.get("minimum")
            maximum = field_schema.get("maximum")
            if minimum is not None and value < minimum:
                return [f"{field_name} must be >= {minimum}"]
            if maximum is not None and value > maximum:
                return [f"{field_name} must be <= {maximum}"]

        if isinstance(value, list):
            item_schema = field_schema.get("items")
            if isinstance(item_schema, dict):
                item_type = item_schema.get("type")
                if item_type is not None:
                    for item in value:
                        if not self._matches_type(value=item, expected_type=item_type):
                            return [f"{field_name} items must be {item_type}"]

        return []

    def _matches_type(self, *, value: Any, expected_type: str | list[str]) -> bool:
        allowed_types = expected_type if isinstance(expected_type, list) else [expected_type]
        for allowed_type in allowed_types:
            if allowed_type == "string" and isinstance(value, str):
                return True
            if allowed_type == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
                return True
            if allowed_type == "boolean" and isinstance(value, bool):
                return True
            if allowed_type == "array" and isinstance(value, list):
                return True
            if allowed_type == "object" and isinstance(value, dict):
                return True
            if allowed_type == "null" and value is None:
                return True
        return False
