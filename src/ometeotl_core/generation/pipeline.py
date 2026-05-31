"""Contextual generation pipeline.

This pipeline starts with deterministic context-to-object generation using explicit
rules and optional validation. LLM-assisted steps can be layered on top of
this pipeline later without changing the core API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ometeotl_core.model.base import ModelObject
from ometeotl_core.model.world import World
from ometeotl_core.validation.base import ValidationResult
from ometeotl_core.validation.pipeline import ValidationPipeline

from .builders import build_from_context
from .context import GenerationContext
from .llm_integration import LLMGenerationAdapter
from .rule_engine import GenerationRuleSet, combined_generation_rules

VALID_GENERATION_OPERATIONS: frozenset[str] = frozenset(
    {"create", "partial_update", "corrective_update"}
)
VALID_REGISTRATION_POLICIES: frozenset[str] = frozenset(
    {"none", "if_available", "require"}
)


@dataclass
class GenerationResult:
    """Structured output of one generation request."""

    generated: Any
    applied_rule_names: list[str] = field(default_factory=list)
    validation: Optional[ValidationResult] = None
    diagnostics: list[str] = field(default_factory=list)
    uncertainty_zones: list[str] = field(default_factory=list)
    repair_suggestions: list[str] = field(default_factory=list)


class ContextualGenerationPipeline:
    """Deterministic contextual generation with optional validation."""

    def __init__(
        self,
        *,
        rules: GenerationRuleSet | None = None,
        validation_pipeline: ValidationPipeline | None = None,
    ) -> None:
        self._rules = rules or combined_generation_rules()
        self._validation_pipeline = validation_pipeline

    @property
    def rules(self) -> GenerationRuleSet:
        return self._rules

    @property
    def validation_pipeline(self) -> ValidationPipeline | None:
        return self._validation_pipeline

    def generate(
        self,
        context: GenerationContext,
        *,
        world: World | None = None,
    ) -> GenerationResult:
        """Generate one object from context using rules then builders."""
        refined_context = self._rules.apply(context)
        operation = str(refined_context.operation or "create")
        if operation not in VALID_GENERATION_OPERATIONS:
            raise ValueError(
                "Unsupported generation operation: "
                f"{operation}. Expected one of {sorted(VALID_GENERATION_OPERATIONS)}"
            )

        registration_policy = str(refined_context.registration_policy or "none")
        if registration_policy not in VALID_REGISTRATION_POLICIES:
            raise ValueError(
                "Unsupported registration policy: "
                f"{registration_policy}. Expected one of {sorted(VALID_REGISTRATION_POLICIES)}"
            )

        validation_result: ValidationResult | None = None
        diagnostics: list[str] = []
        repair_suggestions: list[str] = []

        if operation == "create":
            diagnostics.append("stage: instantiation (create)")
            generated = build_from_context(refined_context)
        else:
            diagnostics.append(f"stage: instantiation ({operation})")
            generated = self._apply_update_operation(
                refined_context,
                world=world,
            )

        uncertainty_zones = self._extract_uncertainty_zones(refined_context)
        if uncertainty_zones:
            diagnostics.append(
                "Explicit uncertainty zones declared: " + ", ".join(uncertainty_zones)
            )

        self._apply_registration_policy(
            refined_context,
            generated,
            world=world,
            diagnostics=diagnostics,
        )

        should_validate = bool(refined_context.validate)
        if should_validate:
            diagnostics.append("stage: validation")
            if self._validation_pipeline is None:
                diagnostics.append(
                    "Validation requested but no validation pipeline is configured"
                )
            else:
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
                    repair_suggestions = self._build_repair_suggestions(
                        validation_result
                    )
                    diagnostics.extend(
                        [f"Suggested repair: {item}" for item in repair_suggestions]
                    )

        return GenerationResult(
            generated=generated,
            applied_rule_names=[rule.name for rule in self._rules.rules],
            validation=validation_result,
            diagnostics=diagnostics,
            uncertainty_zones=uncertainty_zones,
            repair_suggestions=repair_suggestions,
        )

    def generate_from_text_response(
        self,
        context: GenerationContext,
        *,
        raw_response: str,
        llm_adapter: LLMGenerationAdapter,
        fallback_to_base: bool = True,
        world: World | None = None,
    ) -> GenerationResult:
        """Run parsing + deterministic generation from an LLM text response."""
        diagnostics: list[str] = ["stage: parsing"]
        refinement = llm_adapter.refine_context_from_response(
            context,
            raw_response,
            fallback_to_base=fallback_to_base,
        )
        diagnostics.extend(refinement.diagnostics)

        result = self.generate(refinement.refined_context, world=world)
        return GenerationResult(
            generated=result.generated,
            applied_rule_names=result.applied_rule_names,
            validation=result.validation,
            diagnostics=diagnostics + list(result.diagnostics),
            uncertainty_zones=list(result.uncertainty_zones),
            repair_suggestions=list(result.repair_suggestions),
        )

    def generate_hybrid(
        self,
        context: GenerationContext,
        *,
        llm_adapter: LLMGenerationAdapter,
        prompt_template: str | None = None,
        fallback_to_base: bool = True,
        world: World | None = None,
    ) -> GenerationResult:
        """Run LLM-assisted context refinement before deterministic generation."""
        diagnostics: list[str] = ["stage: text_generation"]
        refinement = llm_adapter.refine_context(
            context,
            prompt_template=prompt_template,
            fallback_to_base=fallback_to_base,
        )
        diagnostics.append("stage: parsing")
        diagnostics.extend(refinement.diagnostics)

        result = self.generate(refinement.refined_context, world=world)
        return GenerationResult(
            generated=result.generated,
            applied_rule_names=result.applied_rule_names,
            validation=result.validation,
            diagnostics=diagnostics + list(result.diagnostics),
            uncertainty_zones=list(result.uncertainty_zones),
            repair_suggestions=list(result.repair_suggestions),
        )

    def _extract_uncertainty_zones(
        self,
        context: GenerationContext,
    ) -> list[str]:
        """Extract explicit uncertainty zones from generation context metadata."""
        raw_zones = context.metadata.get("uncertainty_zones") or context.context.get(
            "uncertainty_zones"
        )
        if not raw_zones:
            return []
        if isinstance(raw_zones, str):
            return [raw_zones]
        if isinstance(raw_zones, (list, tuple, set)):
            return [str(item) for item in raw_zones if str(item).strip()]
        return [str(raw_zones)]

    def _build_repair_suggestions(
        self,
        validation_result: ValidationResult,
    ) -> list[str]:
        suggestions: list[str] = []
        for issue in validation_result.errors:
            candidate = issue.suggestion.strip() if issue.suggestion else ""
            if candidate:
                suggestions.append(candidate)
                continue

            location = issue.path or issue.object_id or "target"
            suggestions.append(f"Resolve {issue.code} on {location}: {issue.message}")
        return suggestions

    def _apply_registration_policy(
        self,
        context: GenerationContext,
        generated: Any,
        *,
        world: World | None,
        diagnostics: list[str],
    ) -> None:
        policy = str(context.registration_policy or "none")
        kind = str(context.kind).lower().strip()

        if kind not in {"goal", "strategy", "action", "actor", "resource"}:
            return
        if policy == "none":
            return
        if world is None:
            if policy == "require":
                raise ValueError(
                    "Registration policy 'require' needs a world context for "
                    f"generated {kind} '{context.id}'"
                )
            diagnostics.append(
                f"Skipped registration for {kind} '{context.id}': no world context provided"
            )
            return
        if not isinstance(generated, ModelObject):
            diagnostics.append(
                f"Skipping registration for non-model object generated from kind '{kind}'"
            )
            return

        existing = world.model_registry.get(generated.id)
        if existing is not None:
            diagnostics.append(
                f"Registration skipped for '{generated.id}': object already present in world registry"
            )
            return

        world.register_object(generated)
        diagnostics.append(
            f"Registered generated {kind} '{generated.id}' in world '{world.id}'"
        )

    def _apply_update_operation(
        self,
        context: GenerationContext,
        *,
        world: World | None,
    ) -> ModelObject:
        if world is None:
            raise ValueError(
                f"Operation '{context.operation}' requires a world context"
            )

        target = self._resolve_update_target(context, world)
        operation = str(context.operation)

        if operation == "partial_update":
            self._apply_partial_update(target, context)
            return target
        if operation == "corrective_update":
            self._apply_corrective_update(target, context)
            return target

        raise ValueError(f"Unsupported update operation: {operation}")

    def _resolve_update_target(
        self,
        context: GenerationContext,
        world: World,
    ) -> ModelObject:
        target_id = str(context.target_id or context.id)
        kind = str(context.kind).lower().strip()

        if kind == "world" and target_id == world.id:
            return world

        if kind == "space":
            space = world.get_space(target_id)
            if space is not None:
                return space

        target = world.model_registry.get(target_id)
        if target is None:
            raise ValueError(
                f"Unable to apply {context.operation}: target '{target_id}' does not exist"
            )

        if str(target.object_type).lower() != kind:
            raise ValueError(
                "Target object type mismatch for update operation: "
                f"expected '{kind}', found '{target.object_type}'"
            )

        return target

    def _apply_partial_update(
        self,
        target: ModelObject,
        context: GenerationContext,
    ) -> None:
        for key, value in context.merged_attributes().items():
            target.set_attribute(key, value)

        for key, value in dict(context.state).items():
            target.set_state(key, value)

        self._merge_target_context(target, dict(context.context))

        for key, value in dict(context.provenance).items():
            target.set_provenance(key, value)

        for rel_name, rel_values in context.normalized_relations().items():
            for rel_value in rel_values:
                target.add_relation(rel_name, rel_value)

    def _apply_corrective_update(
        self,
        target: ModelObject,
        context: GenerationContext,
    ) -> None:
        for key, value in context.merged_attributes().items():
            target.set_attribute(key, value)

        for key, value in dict(context.state).items():
            target.set_state(key, value)

        self._merge_target_context(target, dict(context.context))

        for key, value in dict(context.provenance).items():
            target.set_provenance(key, value)

        for rel_name, rel_values in context.normalized_relations().items():
            for existing_target in list(target.relations.get(rel_name, [])):
                target.remove_relation(rel_name, existing_target)
            for rel_value in rel_values:
                target.add_relation(rel_name, rel_value)

    def _merge_target_context(
        self,
        target: ModelObject,
        updates: dict[str, Any],
    ) -> None:
        if not updates:
            return

        merged_context = dict(target.context)
        has_valid_update = False
        for key, value in updates.items():
            if key:
                merged_context[key] = value
                has_valid_update = True

        if not has_valid_update:
            return

        target.context.clear()
        target.context.update(merged_context)
