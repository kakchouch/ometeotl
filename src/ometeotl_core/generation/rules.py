"""Compatibility exports for generation rule APIs.

New code should import from .rule_engine; this module is kept to avoid
breaking existing imports.
"""

from .rule_engine import (  # noqa: F401
    GenerationRule,
    GenerationRuleSet,
    RuleRegistry,
    admissibility_constraint_rules,
    combined_generation_rules,
    default_generation_rules,
    default_rule_registry,
    spatial_constraint_rules,
    temporal_constraint_rules,
)

__all__ = [
    "GenerationRule",
    "GenerationRuleSet",
    "RuleRegistry",
    "default_generation_rules",
    "temporal_constraint_rules",
    "spatial_constraint_rules",
    "admissibility_constraint_rules",
    "combined_generation_rules",
    "default_rule_registry",
]
