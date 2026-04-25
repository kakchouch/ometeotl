"""Epistemic validator for explicit perception-status consistency."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from masm.model.perception import (
    Perception,
    VALID_EPISTEMIC_STATUSES,
)

from .base import (
    SEVERITY_ERROR,
    ValidationContext,
    ValidationIssue,
    ValidationResult,
)


class EpistemicValidator:
    """Validate epistemic statuses in perception-like structures."""

    @property
    def name(self) -> str:
        return "epistemic"

    def validate(
        self, obj: Any, context: ValidationContext
    ) -> ValidationResult:
        issues: list[ValidationIssue] = []

        if isinstance(obj, Perception):
            self._validate_perception_instance(obj, issues)
        elif isinstance(obj, Mapping):
            self._scan_mapping(obj, issues, path="")
        else:
            issues.append(
                ValidationIssue(
                    code="EPI-UNSUPPORTED-TYPE",
                    severity=SEVERITY_ERROR,
                    message=(
                        "Epistemic validation expects Perception or mapping payload"
                    ),
                    context={"input_type": type(obj).__name__},
                )
            )

        return ValidationResult(
            issues=issues,
            stage=context.stage or self.name,
            policy_mode=context.policy_mode,
        )

    def _validate_perception_instance(
        self,
        perception: Perception,
        issues: list[ValidationIssue],
    ) -> None:
        for pm in perception.perceived_memberships:
            self._validate_status(
                pm.epistemic_status,
                issues,
                object_id=perception.id,
                path="perceived_memberships",
            )
        for ps in perception.perceived_spaces.values():
            self._validate_status(
                ps.epistemic_status,
                issues,
                object_id=perception.id,
                path="perceived_spaces",
            )
        for pr in perception.perceived_relations:
            self._validate_status(
                pr.epistemic_status,
                issues,
                object_id=perception.id,
                path="perceived_relations",
            )
        for pcl in perception.perceived_component_links:
            self._validate_status(
                pcl.epistemic_status,
                issues,
                object_id=perception.id,
                path="perceived_component_links",
            )

    def _scan_mapping(
        self,
        value: Mapping[str, Any],
        issues: list[ValidationIssue],
        path: str,
    ) -> None:
        if "epistemic_status" in value:
            self._validate_status(
                value.get("epistemic_status"),
                issues,
                path=(
                    f"{path}.epistemic_status"
                    if path
                    else "epistemic_status"
                ),
            )

        for key, nested in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if isinstance(nested, Mapping):
                self._scan_mapping(nested, issues, child_path)
            elif isinstance(nested, Sequence) and not isinstance(
                nested, (str, bytes)
            ):
                for index, item in enumerate(nested):
                    list_path = f"{child_path}[{index}]"
                    if isinstance(item, Mapping):
                        self._scan_mapping(
                            item, issues, list_path
                        )

    def _validate_status(
        self,
        status: Any,
        issues: list[ValidationIssue],
        *,
        object_id: str = "",
        path: str = "",
    ) -> None:
        if str(status) not in VALID_EPISTEMIC_STATUSES:
            issues.append(
                ValidationIssue(
                    code="EPI-INVALID-STATUS",
                    severity=SEVERITY_ERROR,
                    message=(
                        f"Invalid epistemic status '{status}'. Allowed statuses: "
                        f"{sorted(VALID_EPISTEMIC_STATUSES)}"
                    ),
                    object_id=object_id,
                    path=path,
                )
            )
