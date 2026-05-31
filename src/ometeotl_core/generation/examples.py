"""Runnable demo scenarios for the contextual generation pipeline.

Each function is self-contained and demonstrates one concrete generation
pattern. Run this module directly to see the output of all four scenarios.
"""

from __future__ import annotations

from ometeotl_core.generation.context import GenerationContext, GenerationPlacement
from ometeotl_core.generation.pipeline import ContextualGenerationPipeline
from ometeotl_core.generation.rule_engine import (
    default_rule_registry,
    temporal_constraint_rules,
)
from ometeotl_core.model.world import World
from ometeotl_core.model.actors import Actor
from ometeotl_core.model.perception import Perception
from ometeotl_core.model.goals import Goal

# ---------------------------------------------------------------------------
# Scenario 1 — Simple world: 1 actor, 2 spaces
# ---------------------------------------------------------------------------


def demo_simple_world() -> World:
    """Generate a minimal world with two spaces and one actor.

    Demonstrates: nested context, placement instructions.
    """
    pipeline = ContextualGenerationPipeline()

    ctx = GenerationContext(
        kind="world",
        id="world-demo-1",
        label="Demo World",
        spaces=[
            GenerationContext(kind="space", id="space-alpha", label="Alpha"),
            GenerationContext(kind="space", id="space-beta", label="Beta"),
        ],
        actors=[
            GenerationContext(
                kind="actor",
                id="actor-demo-1",
                label="Explorer",
                attributes={"role": "explorer"},
            )
        ],
        placements=[
            GenerationPlacement(
                object_id="actor-demo-1",
                space_id="space-alpha",
                role="occupies",
            )
        ],
    )

    result = pipeline.generate(ctx)
    world: World = result.generated
    print("[Scenario 1] Simple world")
    print(f"  World id       : {world.id}")
    print(f"  Spaces         : {sorted(world.space_object_graph.spaces.keys())}")
    print(f"  Objects        : {sorted(world.model_registry.all_ids())}")
    print(f"  Rules applied  : {result.applied_rule_names}")
    print()
    return world


# ---------------------------------------------------------------------------
# Scenario 2 — Hierarchical multi-actor world with constraint propagation
# ---------------------------------------------------------------------------


def demo_multi_actor_world() -> World:
    """Generate a world with three actors, two spaces, and temporal constraints.

    Demonstrates: temporal constraint propagation, multiple actors, dedup.
    """
    pipeline = ContextualGenerationPipeline()

    ctx = GenerationContext(
        kind="world",
        id="world-demo-2",
        label="Council Arena",
        constraints={
            "temporal": {"window": 20, "start_step": 5},
            "spatial": {"allowed_spaces": ["north", "south", "north"]},
        },
        spaces=[
            GenerationContext(kind="space", id="north", label="North Quarter"),
            GenerationContext(kind="space", id="south", label="South Quarter"),
        ],
        actors=[
            GenerationContext(
                kind="actor",
                id="actor-alpha",
                label="Alpha",
                attributes={"faction": "red"},
            ),
            GenerationContext(
                kind="actor",
                id="actor-beta",
                label="Beta",
                attributes={"faction": "blue"},
            ),
            GenerationContext(
                kind="actor",
                id="actor-gamma",
                label="Gamma",
                attributes={"faction": "blue"},
            ),
        ],
        placements=[
            GenerationPlacement("actor-alpha", "north"),
            GenerationPlacement("actor-beta", "south"),
            GenerationPlacement("actor-gamma", "south"),
        ],
    )

    result = pipeline.generate(ctx)
    world: World = result.generated
    print("[Scenario 2] Hierarchical multi-actor world")
    print(f"  World id         : {world.id}")
    print(f"  Spaces           : {sorted(world.space_object_graph.spaces.keys())}")
    print(f"  Actors           : {sorted(world.model_registry.all_ids())}")
    print(
        f"  Allowed spaces   : {result.generated.context.get('generation', {}).get('constraints', {}).get('spatial', {})}"
    )
    print(f"  Rules applied    : {result.applied_rule_names}")
    print()
    return world


# ---------------------------------------------------------------------------
# Scenario 3 — Perception generation
# ---------------------------------------------------------------------------


def demo_perception_generation() -> Perception:
    """Generate a perception object for an actor observing a known space.

    Demonstrates: metadata-driven perception, epistemic status.
    """
    registry = default_rule_registry()
    pipeline = ContextualGenerationPipeline(rules=registry.require("default"))

    ctx = GenerationContext(
        kind="perception",
        id="percept-demo-1",
        label="Observer view",
        metadata={
            "actor_id": "actor-observer",
            "source_id": "world-demo-1",
            "timestamp": 42,
            "perceived_spaces": {
                "space-alpha": {
                    "space": {"id": "space-alpha"},
                    "epistemic_status": "certain",
                    "noise_metadata": {},
                }
            },
        },
    )

    result = pipeline.generate(ctx)
    percept: Perception = result.generated
    print("[Scenario 3] Perception generation")
    print(f"  Perception id    : {percept.id}")
    print(f"  Actor id         : {percept.actor_id}")
    print(f"  Source id        : {percept.source_id}")
    print(f"  Perceived spaces : {sorted(percept.perceived_spaces.keys())}")
    print(f"  Rules applied    : {result.applied_rule_names}")
    print()
    return percept


# ---------------------------------------------------------------------------
# Scenario 4 — Goal generation with admissibility constraints
# ---------------------------------------------------------------------------


def demo_goal_generation() -> Goal:
    """Generate a goal for a specific actor with admissibility constraints.

    Demonstrates: admissibility constraint propagation, goal attributes.
    """
    pipeline = ContextualGenerationPipeline()

    ctx = GenerationContext(
        kind="goal",
        id="goal-demo-1",
        label="Reach North Quarter",
        constraints={
            "temporal": {"window": 10},
            "admissibility": {
                "required_capability": "mobility",
                "minimum_confidence": 0.75,
            },
        },
        metadata={
            "actor_id": "actor-alpha",
            "kind": "final",
            "priority": 0.9,
            "status": "active",
            "target_condition": {"location": "north"},
        },
    )

    result = pipeline.generate(ctx)
    goal: Goal = result.generated
    print("[Scenario 4] Goal generation with admissibility constraints")
    print(f"  Goal id              : {goal.id}")
    print(f"  Actor id             : {goal.actor_id}")
    print(f"  Kind / Priority      : {goal.kind} / {goal.priority}")
    print(f"  Target condition     : {goal.target_condition}")
    print(
        f"  Required capability  : {result.generated.context.get('generation', {}).get('constraints', {}).get('admissibility', {})}"
    )
    print(f"  Rules applied        : {result.applied_rule_names}")
    print()
    return goal


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run_all() -> None:
    """Run all demo scenarios in sequence."""
    demo_simple_world()
    demo_multi_actor_world()
    demo_perception_generation()
    demo_goal_generation()


if __name__ == "__main__":
    run_all()
