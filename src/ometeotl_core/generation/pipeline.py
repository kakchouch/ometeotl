"""Contextual generation pipeline.

This pipeline starts with deterministic context-to-object generation using explicit
rules and optional validation. LLM-assisted steps can be layered on top of
this pipeline later without changing the core API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ometeotl_core.validation.base import ValidationResult
from ometeotl_core.validation.pipeline import ValidationPipeline

from .builders import build_from_context
from .context import GenerationContext
from .rules import GenerationRuleSet, default_generation_rules


@dataclass
class GenerationResult:
    """Structured output of one generation request."""

    generated: Any
    applied_rule_names: list[str] = field(default_factory=list)
    validation: Optional[ValidationResult] = None
    diagnostics: list[str] = field(default_factory=list)


class ContextualGenerationPipeline:
    """Deterministic contextual generation with optional validation."""

    def __init__(
        self,
        *,
        rules: GenerationRuleSet | None = None,
        validation_pipeline: ValidationPipeline | None = None,
    ) -> None:
        self._rules = rules or default_generation_rules()
        self._validation_pipeline = validation_pipeline

    @property
    def rules(self) -> GenerationRuleSet:
        return self._rules

    @property
    def validation_pipeline(self) -> ValidationPipeline | None:
        return self._validation_pipeline

    def generate(self, context: GenerationContext) -> GenerationResult:
        """Generate one object from context using rules then builders."""
        refined_context = self._rules.apply(context)
        generated = build_from_context(refined_context)

        validation_result: ValidationResult | None = None
        diagnostics: list[str] = []

        should_validate = bool(refined_context.validate)
        if should_validate and self._validation_pipeline is not None:
            validation_result = self._validation_pipeline.validate(
                generated,
                mode=refined_context.validation_mode,
                stage_modes=refined_context.stage_modes,
                raise_on_error=False,
            )
            if not validation_result.valid:
                diagnostics.append(
                    "Generated object failed validation; inspect validation summary and issues"
                )

        return GenerationResult(
            generated=generated,
            applied_rule_names=[rule.name for rule in self._rules.rules],
            validation=validation_result,
            diagnostics=diagnostics,
        )
