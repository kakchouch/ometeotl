"""Minimal rule engine for contextual generation.

Rules are intentionally simple callables over ``GenerationContext`` so the
pipeline can perform deterministic pre-build adjustments without introducing a
new policy subsystem.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

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


def _normalize_relation_lists(context: GenerationContext) -> GenerationContext:
    return context.copy_with(relations=context.normalized_relations())


def _promote_label_to_attributes(context: GenerationContext) -> GenerationContext:
    return context.copy_with(attributes=context.merged_attributes())


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
