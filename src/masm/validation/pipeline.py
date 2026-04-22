"""Validation pipeline orchestration for explicit staged checks."""

from __future__ import annotations

from typing import Any, Iterable

from .base import (
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    ValidationContext,
    ValidationException,
    ValidationIssue,
    ValidationResult,
    Validator,
)

MODE_STRICT = "strict"
MODE_LENIENT = "lenient"
MODE_WARN_ONLY = "warn_only"

VALID_PIPELINE_MODES: frozenset[str] = frozenset(
    {MODE_STRICT, MODE_LENIENT, MODE_WARN_ONLY}
)


class ValidationPipeline:
    """Run a sequence of validators with a shared policy mode."""

    def __init__(self, validators: Iterable[Validator]):
        self._validators = list(validators)

    @property
    def validators(self) -> list[Validator]:
        return list(self._validators)

    def validate(
        self,
        obj: Any,
        *,
        mode: str = MODE_LENIENT,
        context: ValidationContext | None = None,
        raise_on_error: bool = False,
    ) -> ValidationResult:
        """Run all validators and return one merged ValidationResult.

        ``raise_on_error`` is honored only in strict mode.
        """
        if mode not in VALID_PIPELINE_MODES:
            raise ValueError(f"Unsupported validation mode: {mode}")

        base_context = context or ValidationContext()
        aggregate = ValidationResult(
            stage=base_context.stage,
            policy_mode=mode,
            metadata={
                "executed_validators": [],
            },
        )

        for validator in self._validators:
            stage_context = ValidationContext(
                stage=validator.name,
                policy_mode=mode,
                actor_id=base_context.actor_id,
                world_id=base_context.world_id,
                metadata=dict(base_context.metadata),
            )
            current_result = validator.validate(obj, stage_context)
            normalized_result = self._normalize_result_for_mode(
                current_result,
                mode,
            )
            aggregate = aggregate.merged_with(normalized_result)
            aggregate.metadata["executed_validators"].append(validator.name)

        if mode == MODE_STRICT and raise_on_error and not aggregate.valid:
            raise ValidationException(aggregate)

        return aggregate

    def _normalize_result_for_mode(
        self,
        result: ValidationResult,
        mode: str,
    ) -> ValidationResult:
        if mode != MODE_WARN_ONLY:
            return ValidationResult(
                issues=list(result.issues),
                stage=result.stage,
                policy_mode=mode,
                metadata=dict(result.metadata),
            )

        downgraded_issues: list[ValidationIssue] = []
        for issue in result.issues:
            if issue.severity == SEVERITY_ERROR:
                downgraded_issues.append(
                    ValidationIssue(
                        code=issue.code,
                        severity=SEVERITY_WARNING,
                        message=issue.message,
                        object_id=issue.object_id,
                        path=issue.path,
                        suggestion=issue.suggestion,
                        context=dict(issue.context),
                    )
                )
                continue
            downgraded_issues.append(issue)

        return ValidationResult(
            issues=downgraded_issues,
            stage=result.stage,
            policy_mode=mode,
            metadata=dict(result.metadata),
        )
