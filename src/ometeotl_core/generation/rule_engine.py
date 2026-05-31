"""Pluggable rule engine for contextual generation.

Provides a dedicated registry and constraint propagation rules
(temporal, spatial, admissibility).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

from .context import GenerationContext

GenerationRulePredicate = Callable[[GenerationContext], bool]
GenerationRuleApply = Callable[[GenerationContext], GenerationContext]


@dataclass(frozen=True)
class GenerationRule:
    """One deterministic transformation rule for generation contexts."""

    name: str
    predicate: GenerationRulePredicate
    apply: GenerationRuleApply

    def run(self, context: GenerationContext) -> GenerationContext:
        if self.predicate(context):
            return self.apply(context)
        return context


class GenerationRuleSet:
    """Ordered set of generation rules."""

    def __init__(self, rules: Iterable[GenerationRule] | None = None) -> None:
        self._rules = list(rules or [])

    @property
    def rules(self) -> list[GenerationRule]:
        return list(self._rules)

    def apply(self, context: GenerationContext) -> GenerationContext:
        updated = context
        for rule in self._rules:
            updated = rule.run(updated)
        return updated


class RuleRegistry:
    """Registry of named rule sets for pluggable generation policies."""

    def __init__(self) -> None:
        self._rule_sets: dict[str, GenerationRuleSet] = {}

    def register(self, name: str, rule_set: GenerationRuleSet) -> None:
        normalized = str(name).strip()
        if not normalized:
            raise ValueError("RuleRegistry name cannot be empty")
        self._rule_sets[normalized] = rule_set

    def exists(self, name: str) -> bool:
        return str(name).strip() in self._rule_sets

    def get(self, name: str) -> GenerationRuleSet | None:
        return self._rule_sets.get(str(name).strip())

    def require(self, name: str) -> GenerationRuleSet:
        result = self.get(name)
        if result is None:
            raise KeyError(f"Unknown generation rule set: {name}")
        return result

    def names(self) -> list[str]:
        return sorted(self._rule_sets.keys())


def _normalize_relation_lists(context: GenerationContext) -> GenerationContext:
    return context.copy_with(relations=context.normalized_relations())


def _promote_label_to_attributes(context: GenerationContext) -> GenerationContext:
    return context.copy_with(attributes=context.merged_attributes())


def _coerce_positive_int(value: Any, fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed > 0 else fallback


def _coerce_non_negative_int(value: Any, fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed >= 0 else fallback


def _propagate_temporal_constraints(context: GenerationContext) -> GenerationContext:
    constraints = dict(context.constraints)
    temporal = dict(constraints.get("temporal") or {})
    metadata = dict(context.metadata)

    window = temporal.get("window")
    if window is not None:
        metadata.setdefault("horizon", {})
        horizon = dict(metadata["horizon"])
        horizon.setdefault("window", _coerce_positive_int(window, 1))
        metadata["horizon"] = horizon

    start = temporal.get("start_step")
    if start is not None:
        metadata.setdefault("timeline", {})
        timeline = dict(metadata["timeline"])
        timeline.setdefault("start_step", _coerce_non_negative_int(start, 0))
        metadata["timeline"] = timeline

    return context.copy_with(metadata=metadata)


def _propagate_spatial_constraints(context: GenerationContext) -> GenerationContext:
    constraints = dict(context.constraints)
    spatial = dict(constraints.get("spatial") or {})
    metadata = dict(context.metadata)

    allowed_spaces = spatial.get("allowed_spaces")
    if allowed_spaces:
        if isinstance(allowed_spaces, str):
            allowed_spaces = [allowed_spaces]
        try:
            normalized_spaces = [
                str(space_id) for space_id in allowed_spaces if str(space_id).strip()
            ]
        except TypeError:
            normalized_spaces = []
        if normalized_spaces:
            metadata.setdefault("allowed_spaces", sorted(set(normalized_spaces)))

    required_space = spatial.get("required_space")
    if required_space:
        metadata.setdefault("space_id", str(required_space))

    return context.copy_with(metadata=metadata)


def _propagate_admissibility_constraints(
    context: GenerationContext,
) -> GenerationContext:
    constraints = dict(context.constraints)
    admissibility = dict(constraints.get("admissibility") or {})
    metadata = dict(context.metadata)

    capability = admissibility.get("required_capability")
    if capability:
        metadata.setdefault("required_capability", str(capability))

    threshold = admissibility.get("minimum_confidence")
    if threshold is not None:
        try:
            normalized_threshold = float(threshold)
        except (TypeError, ValueError):
            normalized_threshold = 0.0
        metadata.setdefault(
            "minimum_confidence", max(0.0, min(1.0, normalized_threshold))
        )

    return context.copy_with(metadata=metadata)


def default_generation_rules() -> GenerationRuleSet:
    """Return the default deterministic rule set for generation."""
    return GenerationRuleSet(
        [
            GenerationRule(
                name="normalize_relations",
                predicate=lambda context: bool(context.relations),
                apply=_normalize_relation_lists,
            ),
            GenerationRule(
                name="promote_label",
                predicate=lambda context: bool(context.label),
                apply=_promote_label_to_attributes,
            ),
        ]
    )


def temporal_constraint_rules() -> GenerationRuleSet:
    """Rule set focused on temporal constraint propagation."""
    return GenerationRuleSet(
        [
            GenerationRule(
                name="propagate_temporal_constraints",
                predicate=lambda context: bool(
                    dict(context.constraints).get("temporal")
                ),
                apply=_propagate_temporal_constraints,
            )
        ]
    )


def spatial_constraint_rules() -> GenerationRuleSet:
    """Rule set focused on spatial constraint propagation."""
    return GenerationRuleSet(
        [
            GenerationRule(
                name="propagate_spatial_constraints",
                predicate=lambda context: bool(
                    dict(context.constraints).get("spatial")
                ),
                apply=_propagate_spatial_constraints,
            )
        ]
    )


def admissibility_constraint_rules() -> GenerationRuleSet:
    """Rule set focused on admissibility constraint propagation."""
    return GenerationRuleSet(
        [
            GenerationRule(
                name="propagate_admissibility_constraints",
                predicate=lambda context: bool(
                    dict(context.constraints).get("admissibility")
                ),
                apply=_propagate_admissibility_constraints,
            )
        ]
    )


def combined_generation_rules() -> GenerationRuleSet:
    """Return a combined default rule set including constraint propagation."""
    combined_rules: list[GenerationRule] = []
    combined_rules.extend(default_generation_rules().rules)
    combined_rules.extend(temporal_constraint_rules().rules)
    combined_rules.extend(spatial_constraint_rules().rules)
    combined_rules.extend(admissibility_constraint_rules().rules)
    return GenerationRuleSet(combined_rules)


def default_rule_registry() -> RuleRegistry:
    """Return registry pre-populated with built-in generation rule sets."""
    registry = RuleRegistry()
    registry.register("default", default_generation_rules())
    registry.register("temporal", temporal_constraint_rules())
    registry.register("spatial", spatial_constraint_rules())
    registry.register("admissibility", admissibility_constraint_rules())
    registry.register("combined", combined_generation_rules())
    return registry
