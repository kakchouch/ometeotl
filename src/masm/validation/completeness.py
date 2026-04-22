"""Completeness validator for minimum and recommended object fields."""

from __future__ import annotations

from typing import Any, Mapping

from masm.model.base import ModelObject

from .base import (
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    ValidationContext,
    ValidationIssue,
    ValidationResult,
)

LEVEL_MINIMAL = "minimal"
LEVEL_RECOMMENDED = "recommended"
LEVEL_FULL = "full"

VALID_COMPLETENESS_LEVELS: frozenset[str] = frozenset(
    {LEVEL_MINIMAL, LEVEL_RECOMMENDED, LEVEL_FULL}
)

REQUIRED_FIELDS_BY_TYPE: dict[str, tuple[str, ...]] = {
    "default": ("id", "object_type", "schema_version"),
    "action": ("id", "object_type", "schema_version", "actor_id", "space_id"),
    "goal": ("id", "object_type", "schema_version", "actor_id", "kind"),
    "strategy": (
        "id",
        "object_type",
        "schema_version",
        "actor_id",
        "root_node_id",
    ),
    "perception": (
        "id",
        "actor_id",
        "source_id",
        "schema_version",
    ),
}

RECOMMENDED_FIELDS_BY_TYPE: dict[str, tuple[str, ...]] = {
    "default": ("attributes", "relations", "state", "context", "provenance"),
    "action": ("resource_effects", "prerequisites", "state_changes"),
    "goal": ("target_condition", "horizon", "status"),
    "strategy": ("nodes", "projection_policy"),
    "perception": ("perceived_spaces", "perceived_memberships", "context"),
}


class CompletenessValidator:
    """Validate whether payload/object satisfies configured completeness level."""

    @property
    def name(self) -> str:
        return "completeness"

    def validate(self, obj: Any, context: ValidationContext) -> ValidationResult:
        payload = self._to_mapping(obj)
        if payload is None:
            return ValidationResult(
                issues=[
                    ValidationIssue(
                        code="COMP-UNSUPPORTED-TYPE",
                        severity=SEVERITY_ERROR,
                        message=(
                            "Completeness validation expects mapping-like payload "
                            "or ModelObject"
                        ),
                        context={"input_type": type(obj).__name__},
                    )
                ],
                stage=context.stage or self.name,
                policy_mode=context.policy_mode,
            )

        level = str(context.metadata.get("completeness_level") or LEVEL_MINIMAL)
        if level not in VALID_COMPLETENESS_LEVELS:
            level = LEVEL_MINIMAL

        object_type = str(payload.get("object_type") or "default").lower()
        required_fields = REQUIRED_FIELDS_BY_TYPE.get(
            object_type,
            REQUIRED_FIELDS_BY_TYPE["default"],
        )
        recommended_fields = RECOMMENDED_FIELDS_BY_TYPE.get(
            object_type,
            RECOMMENDED_FIELDS_BY_TYPE["default"],
        )

        issues: list[ValidationIssue] = []
        object_id = str(payload.get("id") or "")

        for field_name in required_fields:
            if self._is_missing(payload.get(field_name)):
                issues.append(
                    ValidationIssue(
                        code="COMP-MISSING-REQUIRED",
                        severity=SEVERITY_ERROR,
                        message=f"Required field '{field_name}' is missing or empty",
                        object_id=object_id,
                        path=field_name,
                    )
                )

        if level in {LEVEL_RECOMMENDED, LEVEL_FULL}:
            for field_name in recommended_fields:
                if self._is_missing(payload.get(field_name)):
                    severity = SEVERITY_WARNING
                    if level == LEVEL_FULL:
                        severity = SEVERITY_ERROR
                    issues.append(
                        ValidationIssue(
                            code="COMP-MISSING-RECOMMENDED",
                            severity=severity,
                            message=f"Recommended field '{field_name}' is missing",
                            object_id=object_id,
                            path=field_name,
                        )
                    )

        return ValidationResult(
            issues=issues,
            stage=context.stage or self.name,
            policy_mode=context.policy_mode,
            metadata={"completeness_level": level},
        )

    def _to_mapping(self, obj: Any) -> Mapping[str, Any] | None:
        if isinstance(obj, Mapping):
            return obj
        if isinstance(obj, ModelObject):
            return obj.to_dict()
        return None

    def _is_missing(self, value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return not value
        if isinstance(value, (list, tuple, dict, set)):
            return len(value) == 0
        return False
