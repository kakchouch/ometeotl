"""Tests for masm.validation.diagnostic."""

from masm.validation.base import (
    SEVERITY_ERROR,
    ValidationIssue,
    ValidationResult,
)
from masm.validation.diagnostic import DiagnosticBuilder


def test_diagnostic_builder_keeps_summary_and_stage():
    """Diagnostic report should preserve validation summary metadata."""
    result = ValidationResult(
        issues=[
            ValidationIssue(
                code="STR-MISSING-ID",
                severity=SEVERITY_ERROR,
                message="Field 'id' is required and cannot be empty",
            )
        ],
        stage="structural",
        policy_mode="lenient",
    )

    report = DiagnosticBuilder().build(result)

    assert report.stage == "structural"
    assert report.policy_mode == "lenient"
    assert report.summary["error"] == 1


def test_diagnostic_builder_adds_default_repair_suggestion():
    """Known issue codes should get a useful default repair suggestion."""
    result = ValidationResult(
        issues=[
            ValidationIssue(
                code="EPI-INVALID-STATUS",
                severity=SEVERITY_ERROR,
                message="Invalid epistemic status 'x'",
            )
        ]
    )

    report = DiagnosticBuilder().build(result)

    assert len(report.diagnostics) == 1
    assert "allowed epistemic statuses" in report.diagnostics[0].suggestion


def test_diagnostic_builder_preserves_explicit_issue_suggestion():
    """Explicit suggestions on issues should not be overwritten."""
    result = ValidationResult(
        issues=[
            ValidationIssue(
                code="CUSTOM-1",
                severity=SEVERITY_ERROR,
                message="custom failure",
                suggestion="use explicit fix",
            )
        ]
    )

    report = DiagnosticBuilder().build(result)

    assert report.diagnostics[0].suggestion == "use explicit fix"
