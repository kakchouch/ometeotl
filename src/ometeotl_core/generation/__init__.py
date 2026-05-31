"""Contextual generation API for ometeotl_core."""

from .context import GenerationContext, GenerationPlacement
from .context_builder import (
    ActorContextualBuilder,
    ContextualBuilder,
    GoalContextualBuilder,
    PerceptionContextualBuilder,
    StrategyContextualBuilder,
    WorldContextualBuilder,
    build_with_context_builder,
    default_contextual_builders,
)
from .llm_integration import LLMGenerationAdapter, LLMRefinementResult
from .pipeline import ContextualGenerationPipeline, GenerationResult
from .rule_engine import (
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
    "GenerationContext",
    "GenerationPlacement",
    "GenerationResult",
    "ContextualBuilder",
    "WorldContextualBuilder",
    "ActorContextualBuilder",
    "StrategyContextualBuilder",
    "GoalContextualBuilder",
    "PerceptionContextualBuilder",
    "default_contextual_builders",
    "build_with_context_builder",
    "GenerationRule",
    "GenerationRuleSet",
    "RuleRegistry",
    "temporal_constraint_rules",
    "spatial_constraint_rules",
    "admissibility_constraint_rules",
    "combined_generation_rules",
    "default_rule_registry",
    "ContextualGenerationPipeline",
    "LLMGenerationAdapter",
    "LLMRefinementResult",
    "default_generation_rules",
]
