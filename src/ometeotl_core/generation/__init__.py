"""Contextual generation API for ometeotl_core."""

from .context import GenerationContext, GenerationPlacement
from .llm_integration import LLMGenerationAdapter, LLMRefinementResult
from .pipeline import ContextualGenerationPipeline, GenerationResult
from .rules import GenerationRule, GenerationRuleSet, default_generation_rules

__all__ = [
    "GenerationContext",
    "GenerationPlacement",
    "GenerationResult",
    "GenerationRule",
    "GenerationRuleSet",
    "ContextualGenerationPipeline",
    "LLMGenerationAdapter",
    "LLMRefinementResult",
    "default_generation_rules",
]
