"""Base contracts for the explicit validation layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"

VALID_SEVERITIES: frozenset[str] = frozenset(
    {SEVERITY_ERROR, SEVERITY_WARNING, SEVERITY_INFO}
)


@dataclass(frozen=True)
class ValidationIssue:
    """One diagnostic entry emitted by a validator."""

    code: str
    severity: str
    message: str
    object_id: str = ""
    path: str = ""
    suggestion: str = ""
    context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("ValidationIssue code cannot be empty")
        if self.severity not in VALID_SEVERITIES:
            raise ValueError(
                f"ValidationIssue severity must be one of {sorted(VALID_SEVERITIES)}"
            )
        if not self.message:
            raise ValueError("ValidationIssue message cannot be empty")


@dataclass(frozen=True)
class ValidationContext:
    """Context shared by validation stages."""

    stage: str = ""
    policy_mode: str = "lenient"
    actor_id: str = ""
    world_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationResult:
    """Structured validation result emitted by one validator or a pipeline."""

    issues: list[ValidationIssue] = field(default_factory=list)
    stage: str = ""
    policy_mode: str = "lenient"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == SEVERITY_ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == SEVERITY_WARNING]

    @property
    def infos(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == SEVERITY_INFO]

    @property
    def valid(self) -> bool:
        return len(self.errors) == 0

    @property
    def summary(self) -> dict[str, int]:
        return {
            SEVERITY_ERROR: len(self.errors),
            SEVERITY_WARNING: len(self.warnings),
            SEVERITY_INFO: len(self.infos),
            "total": len(self.issues),
        }

    def merged_with(self, other: "ValidationResult") -> "ValidationResult":
        """Return a deterministic merge of two validation results."""
        merged_issues = list(self.issues) + list(other.issues)
        merged_stage = other.stage or self.stage
        merged_mode = other.policy_mode or self.policy_mode
        merged_metadata = dict(self.metadata)
        merged_metadata.update(other.metadata)
        return ValidationResult(
            issues=merged_issues,
            stage=merged_stage,
            policy_mode=merged_mode,
            metadata=merged_metadata,
        )


class ValidationException(ValueError):
    """Strict-mode exception carrying a structured validation result."""

    def __init__(self, result: ValidationResult):
        super().__init__(
            "Validation failed with "
            f"{result.summary[SEVERITY_ERROR]} error(s) at stage '{result.stage or 'unknown'}'"
        )
        self.result = result


class Validator(Protocol):
    """Protocol implemented by validation stages."""

    @property
    def name(self) -> str:
        """Stable stage name for reporting and diagnostics."""

    def validate(self, obj: Any, context: ValidationContext) -> ValidationResult:
        """Validate one object with the provided context."""


def issue_from_mapping(data: Mapping[str, Any]) -> ValidationIssue:
    """Construct a ValidationIssue from mapping data."""
    return ValidationIssue(
        code=str(data.get("code") or ""),
        severity=str(data.get("severity") or SEVERITY_ERROR),
        message=str(data.get("message") or ""),
        object_id=str(data.get("object_id") or ""),
        path=str(data.get("path") or ""),
        suggestion=str(data.get("suggestion") or ""),
        context=dict(data.get("context") or {}),
    )
