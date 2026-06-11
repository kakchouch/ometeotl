"""Tests for ometeotl_core.validation.pipeline."""

import pytest

from ometeotl_core.validation.base import (
    SEVERITY_ERROR,
    ValidationContext,
    ValidationIssue,
    ValidationResult,
)
from ometeotl_core.validation.pipeline import (
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

    assert result.metadata["executed_validators"] == [
        "structural",
        "epistemic",
    ]


def test_pipeline_stage_mode_override_keeps_selected_stage_strict():
    """Stage overrides can harden selected validators while global mode stays warn."""
    pipeline = ValidationPipeline(validators=[_FailingValidator()])

    result = pipeline.validate(
        {"id": "obj-4"},
        mode=MODE_WARN_ONLY,
        stage_modes={"structural": MODE_STRICT},
    )

    assert result.valid is False
    assert result.summary["error"] == 1
    assert result.metadata["effective_stage_modes"]["structural"] == MODE_STRICT


def test_pipeline_strict_stage_override_can_raise_in_warn_mode():
    """Strict stage overrides can trigger raising even when global mode is warn."""
    pipeline = ValidationPipeline(validators=[_FailingValidator()])

    with pytest.raises(ValidationException):
        pipeline.validate(
            {"id": "obj-5"},
            mode=MODE_WARN_ONLY,
            stage_modes={"structural": MODE_STRICT},
            raise_on_error=True,
        )
