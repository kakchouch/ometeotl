"""Syntactic validators for raw JSON/YAML payloads."""

from __future__ import annotations

import json
from typing import Any, Mapping

import yaml

from .base import (
    SEVERITY_ERROR,
    SEVERITY_INFO,
    ValidationContext,
    ValidationIssue,
    ValidationResult,
)


class SyntacticValidator:
    """Validate syntax of serialized payloads before structural checks."""

    @property
    def name(self) -> str:
        return "syntactic"

    def validate(
        self, obj: Any, context: ValidationContext
    ) -> ValidationResult:
        issues: list[ValidationIssue] = []

        if isinstance(obj, (Mapping, list)):
            issues.append(
                ValidationIssue(
                    code="SYN-INFO-NATIVE-PAYLOAD",
                    severity=SEVERITY_INFO,
                    message="Payload is already a native Python structure",
                )
            )
            return ValidationResult(
                issues=issues,
                stage=context.stage or self.name,
                policy_mode=context.policy_mode,
                metadata={"input_kind": "native"},
            )

        raw_text = self._coerce_text(obj)
        if raw_text is None:
            issues.append(
                ValidationIssue(
                    code="SYN-UNSUPPORTED-INPUT",
                    severity=SEVERITY_ERROR,
                    message=(
                        "Syntactic validation expects a JSON/YAML string, bytes, "
                        "dict, or list"
                    ),
                    suggestion="Provide a serialized JSON/YAML payload",
                    context={"input_type": type(obj).__name__},
                )
            )
            return ValidationResult(
                issues=issues,
                stage=context.stage or self.name,
                policy_mode=context.policy_mode,
                metadata={"input_kind": type(obj).__name__},
            )

        requested_format = str(
            context.metadata.get("format") or "auto"
        ).lower()
        parsed, fmt, parse_error = self._parse(
            raw_text, requested_format
        )
        if parse_error is not None:
            issues.append(
                ValidationIssue(
                    code="SYN-PARSE-FAILED",
                    severity=SEVERITY_ERROR,
                    message=f"Cannot parse payload as {requested_format}: {parse_error}",
                    suggestion="Ensure payload is valid JSON or YAML syntax",
                )
            )
            return ValidationResult(
                issues=issues,
                stage=context.stage or self.name,
                policy_mode=context.policy_mode,
                metadata={"requested_format": requested_format},
            )

        if not isinstance(parsed, (Mapping, list)):
            issues.append(
                ValidationIssue(
                    code="SYN-PARSED-SCALAR",
                    severity=SEVERITY_INFO,
                    message="Payload parsed successfully but produced a scalar value",
                    context={
                        "parsed_type": type(parsed).__name__
                    },
                )
            )

        return ValidationResult(
            issues=issues,
            stage=context.stage or self.name,
            policy_mode=context.policy_mode,
            metadata={
                "requested_format": requested_format,
                "parsed_format": fmt,
                "parsed_type": type(parsed).__name__,
            },
        )

    def _coerce_text(self, obj: Any) -> str | None:
        if isinstance(obj, str):
            return obj
        if isinstance(obj, bytes):
            try:
                return obj.decode("utf-8")
            except UnicodeDecodeError:
                return None
        return None

    def _parse(
        self,
        payload: str,
        requested_format: str,
    ) -> tuple[Any, str | None, str | None]:
        if requested_format not in {"json", "yaml", "auto"}:
            return (
                None,
                None,
                f"unsupported format hint '{requested_format}'",
            )

        if requested_format == "json":
            return self._parse_json(payload)
        if requested_format == "yaml":
            return self._parse_yaml(payload)

        parsed_json, json_format, json_error = self._parse_json(
            payload
        )
        if json_error is None:
            return parsed_json, json_format, None

        parsed_yaml, yaml_format, yaml_error = self._parse_yaml(
            payload
        )
        if yaml_error is None:
            return parsed_yaml, yaml_format, None

        return (
            None,
            None,
            f"json={json_error}; yaml={yaml_error}",
        )

    def _parse_json(
        self, payload: str
    ) -> tuple[Any, str | None, str | None]:
        try:
            return json.loads(payload), "json", None
        except (TypeError, ValueError) as exc:
            return None, None, str(exc)

    def _parse_yaml(
        self, payload: str
    ) -> tuple[Any, str | None, str | None]:
        try:
            return yaml.safe_load(payload), "yaml", None
        except yaml.YAMLError as exc:
            return None, None, str(exc)
