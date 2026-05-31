"""Tests for contextual generation pipeline."""

from tests.ometeotl_core._artifact_utils import write_json_artifact

from ometeotl_core.generation import (
    ContextualGenerationPipeline,
    GenerationContext,
    GenerationPlacement,
)
from ometeotl_core.model.actions import Action
from ometeotl_core.model.actors import Actor
from ometeotl_core.model.goals import Goal
from ometeotl_core.model.perception import Perception
from ometeotl_core.model.strategies import Strategy
from ometeotl_core.model.world import World


def test_pipeline_generates_world_with_registered_objects_and_placements():
    pipeline = ContextualGenerationPipeline()
    world_context = GenerationContext(
        kind="world",
        id="world-gen-1",
        label="Generated World",
        spaces=[GenerationContext(kind="space", id="zone-a")],
        actors=[GenerationContext(kind="actor", id="actor-a", label="Alice")],
        resources=[GenerationContext(kind="resource", id="resource-a")],
        placements=[GenerationPlacement(object_id="actor-a", space_id="zone-a")],
    )

    result = pipeline.generate(world_context)

    assert isinstance(result.generated, World)
    assert result.generated.get_space("zone-a") is not None
    assert result.generated.model_registry.get("actor-a") is not None
    assert result.generated.model_registry.get("resource-a") is not None
    assert "actor-a" in result.generated.space_object_graph.list_objects_in_space(
        "zone-a"
    )


def test_pipeline_generates_actor_with_label_promoted_to_attributes():
    pipeline = ContextualGenerationPipeline()
    actor_context = GenerationContext(
        kind="actor", id="actor-gen-1", label="Generated Actor"
    )

    result = pipeline.generate(actor_context)

    assert isinstance(result.generated, Actor)
    assert result.generated.label == "Generated Actor"


def test_pipeline_generates_goal_from_metadata():
    pipeline = ContextualGenerationPipeline()
    goal_context = GenerationContext(
        kind="goal",
        id="goal-gen-1",
        metadata={
            "actor_id": "actor-1",
            "kind": "final",
            "priority": 0.7,
            "status": "active",
            "target_condition": {"state": "safe"},
        },
    )

    result = pipeline.generate(goal_context)

    assert isinstance(result.generated, Goal)
    assert result.generated.actor_id == "actor-1"
    assert result.generated.priority == 0.7
    assert result.generated.target_condition == {"state": "safe"}


def test_pipeline_generates_strategy_with_default_single_node():
    pipeline = ContextualGenerationPipeline()
    strategy_context = GenerationContext(
        kind="strategy",
        id="strategy-gen-1",
        metadata={
            "actor_id": "actor-1",
            "goal_id": "goal-1",
            "root_node_id": "node-root",
            "action_id": "action-1",
        },
    )

    result = pipeline.generate(strategy_context)

    assert isinstance(result.generated, Strategy)
    assert result.generated.actor_id == "actor-1"
    assert result.generated.root_node_id == "node-root"
    assert len(result.generated.nodes) == 1
    assert result.generated.nodes[0].action_id == "action-1"


def test_pipeline_generates_action_from_metadata():
    pipeline = ContextualGenerationPipeline()
    action_context = GenerationContext(
        kind="action",
        id="action-gen-1",
        metadata={
            "actor_id": "actor-1",
            "world_id": "world-1",
            "space_id": "zone-a",
            "action_type": "move",
        },
    )

    result = pipeline.generate(action_context)

    assert isinstance(result.generated, Action)
    assert result.generated.actor_id == "actor-1"
    assert result.generated.world_id == "world-1"
    assert result.generated.space_id == "zone-a"
    assert result.generated.action_type == "move"


def test_pipeline_generates_perception_from_context_metadata():
    pipeline = ContextualGenerationPipeline()
    perception_context = GenerationContext(
        kind="perception",
        id="perception-gen-1",
        metadata={
            "actor_id": "actor-1",
            "source_id": "world-1",
            "timestamp": 42,
            "perceived_spaces": {
                "zone-a": {
                    "space": {"id": "zone-a", "object_type": "space"},
                    "epistemic_status": "certain",
                }
            },
            "perceived_memberships": [
                {
                    "membership": {
                        "object_id": "actor-1",
                        "space_id": "zone-a",
                        "role": "occupies",
                    },
                    "epistemic_status": "believed",
                }
            ],
            "perceived_relations": [
                {
                    "relation": {
                        "source_space_id": "zone-a",
                        "target_space_id": "zone-b",
                        "relation_type": "adjacent_to",
                    },
                    "epistemic_status": "hypothesis",
                }
            ],
            "perceived_component_links": [
                {
                    "link_id": "link-1",
                    "composite_id": "actor-1",
                    "component_id": "actor-2",
                    "epistemic_status": "projected",
                }
            ],
        },
    )

    result = pipeline.generate(perception_context)

    assert isinstance(result.generated, Perception)
    assert result.generated.actor_id == "actor-1"
    assert result.generated.source_id == "world-1"
    assert result.generated.timestamp == 42
    assert sorted(result.generated.perceived_spaces.keys()) == ["zone-a"]
    assert len(result.generated.perceived_memberships) == 1
    assert len(result.generated.perceived_relations) == 1
    assert len(result.generated.perceived_component_links) == 1


def test_generation_audit_writes_local_lab_artifact():
    """Write a stable generation snapshot under local_lab for audit review."""
    pipeline = ContextualGenerationPipeline()

    generated_world = pipeline.generate(
        GenerationContext(
            kind="world",
            id="world-audit-1",
            spaces=[GenerationContext(kind="space", id="zone-a")],
            actors=[GenerationContext(kind="actor", id="actor-a", label="Alice")],
            resources=[GenerationContext(kind="resource", id="resource-a")],
            placements=[GenerationPlacement(object_id="actor-a", space_id="zone-a")],
        )
    ).generated
    generated_strategy = pipeline.generate(
        GenerationContext(
            kind="strategy",
            id="strategy-audit-1",
            metadata={
                "actor_id": "actor-a",
                "goal_id": "goal-a",
                "root_node_id": "node-root",
                "action_id": "action-a",
            },
        )
    ).generated
    generated_perception = pipeline.generate(
        GenerationContext(
            kind="perception",
            id="perception-audit-1",
            metadata={
                "actor_id": "actor-a",
                "source_id": "world-audit-1",
                "perceived_spaces": {
                    "zone-a": {
                        "space": {"id": "zone-a", "object_type": "space"},
                        "epistemic_status": "certain",
                    }
                },
            },
        )
    ).generated

    payload = {
        "world": generated_world.to_dict(),
        "strategy": generated_strategy.to_dict(),
        "perception": generated_perception.to_dict(),
    }
    artifact_path = write_json_artifact(
        layer="generation",
        name="generation_snapshot",
        payload=payload,
    )

    assert artifact_path.name == "generation_snapshot.json"
