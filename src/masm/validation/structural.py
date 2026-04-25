"""Structural validators for typed model payloads and hierarchies."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Mapping

from masm.model.base import ModelObject, SUPPORTED_SCHEMA_VERSION
from masm.model.goals import GoalDecompositionTree
from masm.model.strategies import Strategy

from .base import (
    SEVERITY_ERROR,
    ValidationContext,
    ValidationIssue,
    ValidationResult,
)


class StructuralValidator:
    """Validate object shape, required fields, and hierarchy integrity."""

    @property
    def name(self) -> str:
        return "structural"

    def validate(
        self, obj: Any, context: ValidationContext
    ) -> ValidationResult:
        issues: list[ValidationIssue] = []

        if isinstance(obj, GoalDecompositionTree):
            self._validate_goal_tree_instance(obj, issues)
            return self._result(context, issues)

        if isinstance(obj, Strategy):
            self._validate_strategy_instance(obj, issues)
            return self._result(context, issues)

        if isinstance(obj, ModelObject):
            self._validate_model_instance(obj, issues)
            return self._result(context, issues)

        if isinstance(obj, Mapping):
            self._validate_mapping_payload(obj, issues)
            return self._result(context, issues)

        issues.append(
            ValidationIssue(
                code="STR-UNSUPPORTED-TYPE",
                severity=SEVERITY_ERROR,
                message="Structural validation expects a mapping or model object",
                suggestion="Provide a dict payload or a model instance",
                context={"input_type": type(obj).__name__},
            )
        )
        return self._result(context, issues)

    def _result(
        self,
        context: ValidationContext,
        issues: list[ValidationIssue],
    ) -> ValidationResult:
        return ValidationResult(
            issues=issues,
            stage=context.stage or self.name,
            policy_mode=context.policy_mode,
        )

    def _validate_model_instance(
        self,
        obj: ModelObject,
        issues: list[ValidationIssue],
    ) -> None:
        if not obj.id:
            issues.append(
                ValidationIssue(
                    code="STR-MISSING-ID",
                    severity=SEVERITY_ERROR,
                    message="Model object id cannot be empty",
                    object_id=str(obj.id or ""),
                )
            )

        if not obj.object_type:
            issues.append(
                ValidationIssue(
                    code="STR-MISSING-OBJECT-TYPE",
                    severity=SEVERITY_ERROR,
                    message="Model object type cannot be empty",
                    object_id=str(obj.id or ""),
                )
            )

        if str(obj.schema_version) != SUPPORTED_SCHEMA_VERSION:
            issues.append(
                ValidationIssue(
                    code="STR-SCHEMA-VERSION",
                    severity=SEVERITY_ERROR,
                    message=(
                        "Unsupported schema_version: "
                        f"{obj.schema_version}. Expected {SUPPORTED_SCHEMA_VERSION}"
                    ),
                    object_id=str(obj.id or ""),
                )
            )

        self._validate_map_field(
            obj.attributes,
            "attributes",
            str(obj.id or ""),
            issues,
        )
        self._validate_map_field(
            obj.state, "state", str(obj.id or ""), issues
        )
        self._validate_map_field(
            obj.context, "context", str(obj.id or ""), issues
        )
        self._validate_map_field(
            obj.provenance,
            "provenance",
            str(obj.id or ""),
            issues,
        )

        if not isinstance(obj.relations, Mapping):
            issues.append(
                ValidationIssue(
                    code="STR-RELATIONS-TYPE",
                    severity=SEVERITY_ERROR,
                    message="relations must be a mapping",
                    object_id=str(obj.id or ""),
                    path="relations",
                )
            )
        else:
            self._validate_relations_mapping(
                obj.relations,
                object_id=str(obj.id or ""),
                issues=issues,
            )

    def _validate_mapping_payload(
        self,
        payload: Mapping[str, Any],
        issues: list[ValidationIssue],
    ) -> None:
        if "root_goal_id" in payload and "goals" in payload:
            self._validate_goal_tree_payload(payload, issues)
            return

        inferred_type = str(
            payload.get("object_type") or ""
        ).lower()
        if inferred_type == "strategy":
            self._validate_strategy_payload(payload, issues)
            return

        self._validate_model_payload(payload, issues)

    def _validate_model_payload(
        self,
        payload: Mapping[str, Any],
        issues: list[ValidationIssue],
    ) -> None:
        object_id = str(payload.get("id") or "")

        if not object_id:
            issues.append(
                ValidationIssue(
                    code="STR-MISSING-ID",
                    severity=SEVERITY_ERROR,
                    message="Field 'id' is required and cannot be empty",
                    path="id",
                )
            )

        object_type = str(payload.get("object_type") or "")
        if not object_type:
            issues.append(
                ValidationIssue(
                    code="STR-MISSING-OBJECT-TYPE",
                    severity=SEVERITY_ERROR,
                    message="Field 'object_type' is required and cannot be empty",
                    object_id=object_id,
                    path="object_type",
                )
            )

        schema_version = payload.get(
            "schema_version", SUPPORTED_SCHEMA_VERSION
        )
        if str(schema_version) != SUPPORTED_SCHEMA_VERSION:
            issues.append(
                ValidationIssue(
                    code="STR-SCHEMA-VERSION",
                    severity=SEVERITY_ERROR,
                    message=(
                        "Unsupported schema_version: "
                        f"{schema_version}. Expected {SUPPORTED_SCHEMA_VERSION}"
                    ),
                    object_id=object_id,
                    path="schema_version",
                )
            )

        for field_name in (
            "attributes",
            "state",
            "context",
            "provenance",
        ):
            if field_name in payload:
                self._validate_map_field(
                    payload.get(field_name),
                    field_name,
                    object_id,
                    issues,
                )

        if "relations" in payload:
            relations_value = payload.get("relations")
            if not isinstance(relations_value, Mapping):
                issues.append(
                    ValidationIssue(
                        code="STR-RELATIONS-TYPE",
                        severity=SEVERITY_ERROR,
                        message="Field 'relations' must be a mapping",
                        object_id=object_id,
                        path="relations",
                    )
                )
            else:
                self._validate_relations_mapping(
                    relations_value, object_id, issues
                )

    def _validate_goal_tree_instance(
        self,
        tree: GoalDecompositionTree,
        issues: list[ValidationIssue],
    ) -> None:
        try:
            tree.validate_tree()
        except ValueError as exc:
            issues.append(
                ValidationIssue(
                    code="STR-GOAL-TREE",
                    severity=SEVERITY_ERROR,
                    message=str(exc),
                    object_id=str(tree.root_goal_id),
                )
            )

    def _validate_goal_tree_payload(
        self,
        payload: Mapping[str, Any],
        issues: list[ValidationIssue],
    ) -> None:
        try:
            GoalDecompositionTree.from_dict(payload)
        except (TypeError, ValueError) as exc:
            issues.append(
                ValidationIssue(
                    code="STR-GOAL-TREE",
                    severity=SEVERITY_ERROR,
                    message=str(exc),
                    object_id=str(
                        payload.get("root_goal_id") or ""
                    ),
                )
            )

    def _validate_strategy_instance(
        self,
        strategy: Strategy,
        issues: list[ValidationIssue],
    ) -> None:
        self._validate_model_instance(strategy, issues)
        try:
            strategy.validate_tree()
        except ValueError as exc:
            issues.append(
                ValidationIssue(
                    code="STR-STRATEGY-TREE",
                    severity=SEVERITY_ERROR,
                    message=str(exc),
                    object_id=str(strategy.id or ""),
                )
            )

    def _validate_strategy_payload(
        self,
        payload: Mapping[str, Any],
        issues: list[ValidationIssue],
    ) -> None:
        self._validate_model_payload(payload, issues)
        try:
            strategy = Strategy.from_dict(payload)
            strategy.validate_tree()
        except (TypeError, ValueError) as exc:
            issues.append(
                ValidationIssue(
                    code="STR-STRATEGY-TREE",
                    severity=SEVERITY_ERROR,
                    message=str(exc),
                    object_id=str(payload.get("id") or ""),
                )
            )

    def _validate_map_field(
        self,
        value: Any,
        field_name: str,
        object_id: str,
        issues: list[ValidationIssue],
    ) -> None:
        if not isinstance(value, Mapping):
            issues.append(
                ValidationIssue(
                    code="STR-FIELD-TYPE",
                    severity=SEVERITY_ERROR,
                    message=f"Field '{field_name}' must be a mapping",
                    object_id=object_id,
                    path=field_name,
                )
            )

    def _validate_relations_mapping(
        self,
        relations: Mapping[str, Any],
        object_id: str,
        issues: list[ValidationIssue],
    ) -> None:
        for relation_name, targets in relations.items():
            if not isinstance(targets, Sequence) or isinstance(
                targets, (str, bytes)
            ):
                issues.append(
                    ValidationIssue(
                        code="STR-RELATION-TARGETS-TYPE",
                        severity=SEVERITY_ERROR,
                        message=(
                            "Relation targets must be a list-like sequence of "
                            "non-empty string IDs"
                        ),
                        object_id=object_id,
                        path=f"relations.{relation_name}",
                    )
                )
                continue

            for index, target in enumerate(targets):
                if not isinstance(target, str) or not target:
                    issues.append(
                        ValidationIssue(
                            code="STR-RELATION-TARGET-ID",
                            severity=SEVERITY_ERROR,
                            message="Relation target IDs must be non-empty strings",
                            object_id=object_id,
                            path=f"relations.{relation_name}[{index}]",
                        )
                    )
