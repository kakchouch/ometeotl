"""Tests for masm.validation.pipeline."""

import pytest

from masm.validation.base import (
    SEVERITY_ERROR,
    ValidationContext,
    ValidationIssue,
    ValidationResult,
)
from masm.validation.pipeline import (
    MODE_STRICT,
    MODE_WARN_ONLY,
    ValidationException,
    ValidationPipeline,
)


class _FailingValidator:
    @property
    def name(self) -> str:
        return "structural"

    def validate(self, obj, context: ValidationContext) -> ValidationResult:
        return ValidationResult(
            issues=[
                ValidationIssue(
                    code="STRUCT-001",
                    severity=SEVERITY_ERROR,
                    message=f"Invalid payload for {obj['id']}",
                    object_id=str(obj["id"]),
                )
            ],
            stage=context.stage,
            policy_mode=context.policy_mode,
        )


class _InfoValidator:
    @property
    def name(self) -> str:
        return "epistemic"

    def validate(self, obj, context: ValidationContext) -> ValidationResult:
        return ValidationResult(stage=context.stage, policy_mode=context.policy_mode)


def test_pipeline_warn_only_downgrades_errors():
    """warn_only mode converts errors to warnings for soft-gate integration."""
    pipeline = ValidationPipeline(validators=[_FailingValidator()])

    result = pipeline.validate({"id": "obj-1"}, mode=MODE_WARN_ONLY)

    assert result.valid is True
    assert result.summary["error"] == 0
    assert result.summary["warning"] == 1


def test_pipeline_strict_can_raise_with_structured_payload():
    """Strict mode optionally raises while preserving ValidationResult."""
    pipeline = ValidationPipeline(validators=[_FailingValidator()])

    with pytest.raises(ValidationException) as exc_info:
        pipeline.validate(
            {"id": "obj-2"},
            mode=MODE_STRICT,
            raise_on_error=True,
        )

    assert exc_info.value.result.summary["error"] == 1


def test_pipeline_reports_executed_validators_order():
    """Pipeline metadata tracks stage execution order deterministically."""
    pipeline = ValidationPipeline(validators=[_FailingValidator(), _InfoValidator()])

    result = pipeline.validate({"id": "obj-3"})

    assert result.metadata["executed_validators"] == ["structural", "epistemic"]
