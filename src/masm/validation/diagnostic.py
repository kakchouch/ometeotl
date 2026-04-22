"""Diagnostic and repair helpers for validation results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .base import ValidationIssue, ValidationResult


@dataclass(frozen=True)
class DiagnosticEntry:
    """One motivated diagnostic item derived from a validation issue."""

    code: str
    severity: str
    reason: str
    object_id: str = ""
    path: str = ""
    suggestion: str = ""
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "reason": self.reason,
            "object_id": self.object_id,
            "path": self.path,
            "suggestion": self.suggestion,
            "context": dict(self.context),
        }


@dataclass(frozen=True)
class DiagnosticReport:
    """Collection of diagnostics plus aggregate metadata."""

    diagnostics: list[DiagnosticEntry] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)
    stage: str = ""
    policy_mode: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "diagnostics": [entry.to_dict() for entry in self.diagnostics],
            "summary": dict(self.summary),
            "stage": self.stage,
            "policy_mode": self.policy_mode,
        }


class DiagnosticBuilder:
    """Build actionable diagnostics and repair hints from validation output."""

    def build(self, result: ValidationResult) -> DiagnosticReport:
        diagnostics = [self._entry_from_issue(issue) for issue in result.issues]
        return DiagnosticReport(
            diagnostics=diagnostics,
            summary=result.summary,
            stage=result.stage,
            policy_mode=result.policy_mode,
        )

    def _entry_from_issue(self, issue: ValidationIssue) -> DiagnosticEntry:
        suggestion = issue.suggestion or self._default_suggestion(issue)
        reason = issue.message
        return DiagnosticEntry(
            code=issue.code,
            severity=issue.severity,
            reason=reason,
            object_id=issue.object_id,
            path=issue.path,
            suggestion=suggestion,
            context=dict(issue.context),
        )

    def _default_suggestion(self, issue: ValidationIssue) -> str:
        code = issue.code

        if code in {
            "STR-MISSING-ID",
            "STR-MISSING-OBJECT-TYPE",
            "COMP-MISSING-REQUIRED",
        }:
            return "Provide the missing required field with a non-empty value"

        if code in {
            "STR-RELATION-TARGET-ID",
            "STR-RELATION-TARGETS-TYPE",
            "STR-GOAL-TREE",
            "STR-STRATEGY-TREE",
        }:
            return "Fix relation references so all IDs and hierarchy links are valid"

        if code in {
            "EPI-INVALID-STATUS",
        }:
            return (
                "Use one of the allowed epistemic statuses: certain, believed, "
                "hypothesis, projected, error"
            )

        if code in {
            "SYN-PARSE-FAILED",
            "SYN-UNSUPPORTED-INPUT",
        }:
            return "Fix payload syntax and provide valid JSON or YAML"

        if code in {
            "SPATIAL-UNKNOWN-SPACE",
            "SPATIAL-ACTOR-NOT-IN-SPACE",
            "SPATIAL-NO-SHARED-SPACE",
        }:
            return (
                "Align space references and memberships before issuing this interaction"
            )

        if code in {
            "TEMP-OUTSIDE-VALIDITY",
        }:
            return "Adjust interaction time or actor validity window to overlap"

        if code in {
            "ADM-NOT-ADMISSIBLE",
        }:
            return "Adjust goal/actor linkage or perceived constraints to satisfy admissibility"

        return "Inspect the issue context and update payload/model accordingly"
