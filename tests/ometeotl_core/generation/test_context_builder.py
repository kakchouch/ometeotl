"""Tests for class-based contextual builders."""

import pytest

from ometeotl_core.generation import (
    ActorContextualBuilder,
    GenerationContext,
    GenerationPlacement,
    WorldContextualBuilder,
    build_with_context_builder,
    default_contextual_builders,
)
from ometeotl_core.model.actors import Actor
from ometeotl_core.model.world import World


def test_generation_context_exposes_rules_and_constraints_in_merged_context():
    context = GenerationContext(
        kind="actor",
        id="actor-cb-1",
        metadata={"source": "test"},
        rules={"label_policy": "strict"},
        constraints={"max_links": 4},
    )

    merged = context.merged_context()

    assert "generation" in merged
    assert merged["generation"]["source"] == "test"
    assert merged["generation"]["rules"] == {"label_policy": "strict"}
    assert merged["generation"]["constraints"] == {"max_links": 4}


def test_default_contextual_builders_cover_core_context_kinds():
    builder_map = default_contextual_builders()

    assert sorted(builder_map.keys()) == [
        "actor",
        "goal",
        "perception",
        "strategy",
        "world",
    ]


def test_build_with_context_builder_builds_actor():
    generated = build_with_context_builder(
        GenerationContext(kind="actor", id="actor-cb-2", label="Builder Actor")
    )

    assert isinstance(generated, Actor)
    assert generated.id == "actor-cb-2"
    assert generated.label == "Builder Actor"


def test_builder_raises_on_kind_mismatch():
    builder = ActorContextualBuilder()

    with pytest.raises(ValueError, match="expects kind 'actor'"):
        builder.build(GenerationContext(kind="world", id="world-cb-1"))


def test_world_contextual_builder_builds_nested_world_with_placements():
    builder = WorldContextualBuilder()
    world = builder.build(
        GenerationContext(
            kind="world",
            id="world-cb-3",
            spaces=[GenerationContext(kind="space", id="zone-cb")],
            actors=[GenerationContext(kind="actor", id="actor-cb-3")],
            placements=[
                GenerationPlacement(object_id="actor-cb-3", space_id="zone-cb")
            ],
        )
    )

    assert isinstance(world, World)
    assert world.get_space("zone-cb") is not None
    assert world.model_registry.exists("actor-cb-3")
    assert "actor-cb-3" in world.space_object_graph.list_objects_in_space("zone-cb")
