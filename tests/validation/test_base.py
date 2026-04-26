"""Tests for ometeotl_core.validation.base."""

import pytest

from ometeotl_core.validation.base import (
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    ValidationException,
    ValidationIssue,
    ValidationResult,
    issue_from_mapping,
)


def test_validation_issue_rejects_invalid_severity():
    """ValidationIssue rejects severities outside the contract."""
    with pytest.raises(ValueError, match="severity"):
        ValidationIssue(
            code="X", severity="fatal", message="bad"
        )


def test_validation_result_summary_and_valid_property():
    """ValidationResult exposes deterministic severity summaries."""
    result = ValidationResult(
        issues=[
            ValidationIssue(
                code="E1",
                severity=SEVERITY_ERROR,
                message="error",
            ),
            ValidationIssue(
                code="W1",
                severity=SEVERITY_WARNING,
                message="warn",
            ),
            ValidationIssue(
                code="I1", severity=SEVERITY_INFO, message="info"
            ),
        ],
        stage="structural",
    )

    assert result.valid is False
    assert result.summary == {
        SEVERITY_ERROR: 1,
        SEVERITY_WARNING: 1,
        SEVERITY_INFO: 1,
        "total": 3,
    }


def test_validation_exception_carries_result():
    """Strict-mode errors can be surfaced with the original result payload."""
    result = ValidationResult(
        issues=[
            ValidationIssue(
                code="E1",
                severity=SEVERITY_ERROR,
                message="error",
            ),
        ],
        stage="epistemic",
    )

    exc = ValidationException(result)

    assert exc.result is result
    assert "1 error" in str(exc)


def test_issue_from_mapping_defaults_to_error():
    """Mapping conversion defaults severity to error when omitted."""
    issue = issue_from_mapping(
        {"code": "E2", "message": "missing field"}
    )

    assert issue.severity == SEVERITY_ERROR
    assert issue.code == "E2"
