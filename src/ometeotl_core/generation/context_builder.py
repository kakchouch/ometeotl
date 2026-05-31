"""Class-based contextual builders for generation.

This module provides a typed builder abstraction on top of the existing
function-based builders so callers can compose or override per-kind behavior
without changing the generation pipeline contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from ometeotl_core.model.actors import Actor
from ometeotl_core.model.goals import Goal
from ometeotl_core.model.perception import Perception
from ometeotl_core.model.strategies import Strategy
from ometeotl_core.model.world import World

from .builders import (
    build_actor,
    build_goal,
    build_perception,
    build_strategy,
    build_world,
)
from .context import GenerationContext

TGenerated = TypeVar("TGenerated")


class ContextualBuilder(ABC, Generic[TGenerated]):
    """Base class for kind-specific generation context builders."""

    kind: str

    def ensure_kind(self, context: GenerationContext) -> None:
        """Validate the context kind routed to this builder."""
        if str(context.kind).lower().strip() != self.kind:
            raise ValueError(
                f"Builder '{self.__class__.__name__}' expects kind '{self.kind}', "
                f"received '{context.kind}'"
            )

    @abstractmethod
    def build(self, context: GenerationContext) -> TGenerated:
        """Build one object from a generation context."""


class WorldContextualBuilder(ContextualBuilder[World]):
    """Build world objects from generation context."""

    kind = "world"

    def build(self, context: GenerationContext) -> World:
        self.ensure_kind(context)
        return build_world(context)


class ActorContextualBuilder(ContextualBuilder[Actor]):
    """Build actor objects from generation context."""

    kind = "actor"

    def build(self, context: GenerationContext) -> Actor:
        self.ensure_kind(context)
        return build_actor(context)


class StrategyContextualBuilder(ContextualBuilder[Strategy]):
    """Build strategy objects from generation context."""

    kind = "strategy"

    def build(self, context: GenerationContext) -> Strategy:
        self.ensure_kind(context)
        return build_strategy(context)


class GoalContextualBuilder(ContextualBuilder[Goal]):
    """Build goal objects from generation context."""

    kind = "goal"

    def build(self, context: GenerationContext) -> Goal:
        self.ensure_kind(context)
        return build_goal(context)


class PerceptionContextualBuilder(ContextualBuilder[Perception]):
    """Build perception objects from generation context."""

    kind = "perception"

    def build(self, context: GenerationContext) -> Perception:
        self.ensure_kind(context)
        return build_perception(context)


def default_contextual_builders() -> dict[str, ContextualBuilder[Any]]:
    """Return default builder instances keyed by generation kind."""
    return {
        "world": WorldContextualBuilder(),
        "actor": ActorContextualBuilder(),
        "strategy": StrategyContextualBuilder(),
        "goal": GoalContextualBuilder(),
        "perception": PerceptionContextualBuilder(),
    }


def build_with_context_builder(
    context: GenerationContext,
    *,
    builders: dict[str, ContextualBuilder[Any]] | None = None,
) -> Any:
    """Build one object via the class-based builder registry."""
    builder_map = builders or default_contextual_builders()
    kind = str(context.kind).lower().strip()
    builder = builder_map.get(kind)
    if builder is None:
        raise ValueError(f"Unsupported generation kind for class-based builder: {kind}")
    return builder.build(context)
