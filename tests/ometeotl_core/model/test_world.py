"""Tests for ometeotl_core.model.world."""

import pytest

from ometeotl_core.model.actors import Actor
from ometeotl_core.model.registry import MinimalModelRegistry
from ometeotl_core.model.resources import Resource
from ometeotl_core.model.space_relations import SpaceRelation
from ometeotl_core.model.spaces import Space
from ometeotl_core.model.world import World


def test_world_instantiation():
    """Verify that a world instantiates correctly."""
    world = World(id="world-0")

    assert world.id == "world-0"
    assert world.object_type == "world"
    assert world.kind == "world"
    assert world.is_root_world is True


def test_world_add_subspace():
    """Verify that a sub-space can be added to a world and retrieved by ID."""
    world = World(id="world-1")
    sub = Space(id="zone-a")

    world.add_space(sub)

    assert world.get_space("zone-a") is sub
    assert world.get_space("zone-b") is None


def test_world_add_duplicate_subspace_raises():
    """Verify that adding a sub-space with a duplicate ID raises ValueError."""
    world = World(id="world-2")
    sub = Space(id="zone-a")
    world.add_space(sub)

    with pytest.raises(ValueError):
        world.add_space(Space(id="zone-a"))


def test_world_place_object_in_subspace():
    """Verify that an object can be placed in a sub-space."""
    world = World(id="world-3")
    sub = Space(id="zone-b")
    world.add_space(sub)
    world.place_object("actor-1", "zone-b", role="occupies")

    members = world.space_object_graph.list_objects_in_space(
        "zone-b"
    )
    assert "actor-1" in members


def test_world_place_object_unknown_space_raises():
    """Verify that placing an object in an unknown space raises ValueError."""
    world = World(id="world-4")

    with pytest.raises(ValueError):
        world.place_object("actor-1", "nonexistent-space")


def test_world_add_space_relation():
    """Verify that a space relation can be added between two sub-spaces."""
    world = World(id="world-5")
    world.add_space(Space(id="s1"))
    world.add_space(Space(id="s2"))

    world.add_space_relation(
        SpaceRelation(
            source_space_id="s1",
            target_space_id="s2",
            relation_type="adjacent_to",
        )
    )

    neighbors = world.space_relation_graph.neighbors_of("s1")
    assert "s2" in neighbors


def test_world_register_and_unregister_object():
    """Verify that objects are tracked only in the world-scoped registry."""
    MinimalModelRegistry.clear()
    world = World(id="world-6")
    actor = Actor(id="actor-reg-1")

    world.register_object(actor)
    assert world.model_registry.exists("actor-reg-1")
    assert not MinimalModelRegistry.exists("actor-reg-1")

    world.unregister_object("actor-reg-1")
    assert not world.model_registry.exists("actor-reg-1")
    assert not MinimalModelRegistry.exists("actor-reg-1")

    MinimalModelRegistry.clear()


def test_object_register_and_place():
    """Test that _object_register_and_place registers and places the object in one step."""
    world = World(id="test-world")
    space = Space(id="test-space")
    world.add_space(space)
    actor = Actor(id="test-actor")

    world.add_object_to_space(
        actor, "test-space", role="occupies"
    )

    # Check registration
    assert world.model_registry.exists("test-actor")
    # Check placement
    members = world.space_object_graph.list_objects_in_space(
        "test-space"
    )
    assert "test-actor" in members


def test_world_to_dict_contains_required_fields():
    """Verify that World.to_dict() exports all mandatory canonical fields."""
    world = World(id="world-7")
    payload = world.to_dict()

    required = {
        "id",
        "object_type",
        "schema_version",
        "attributes",
        "relations",
        "state",
        "context",
        "provenance",
        "space_object_graph",
        "space_relation_graph",
    }
    assert required.issubset(payload.keys())
    assert payload["object_type"] == "world"
    assert payload["attributes"]["kind"] == "world"
    assert payload["attributes"]["is_root_world"] is True


def test_world_to_dict_roundtrip():
    """Verify that a world can be serialized and reconstructed without loss."""
    world = World(id="world-8")
    world.label = "Test World"
    world.add_space(Space(id="s1"))
    world.add_space(Space(id="s2"))
    world.place_object("actor-x", "s1", role="occupies")
    world.add_space_relation(
        SpaceRelation(
            source_space_id="s1",
            target_space_id="s2",
            relation_type="adjacent_to",
        )
    )

    restored = World.from_dict(world.to_dict())

    assert restored.id == "world-8"
    assert restored.object_type == "world"
    assert restored.kind == "world"
    assert restored.is_root_world is True
    assert restored.label == "Test World"
    assert restored.get_space("s1") is not None
    assert restored.get_space("s2") is not None
    assert (
        "actor-x"
        in restored.space_object_graph.list_objects_in_space(
            "s1"
        )
    )
    assert "s2" in restored.space_relation_graph.neighbors_of(
        "s1"
    )


def test_world_spaces_where_object_exists():
    """Verify that a world can report all sub-spaces for one object."""
    world = World(id="world-9")
    world.add_space(Space(id="phys"))
    world.add_space(Space(id="info"))
    world.place_object("actor-multi", "phys")
    world.place_object("actor-multi", "info")

    spaces = world.space_object_graph.spaces_where_object_exists(
        "actor-multi"
    )
    space_ids = [space.id for space in spaces]
    assert "phys" in space_ids
    assert "info" in space_ids


def test_world_to_dict_roundtrip_preserves_registered_objects():
    """World roundtrip preserves registered object instances and their types."""
    world = World(id="world-10")
    actor = Actor(id="actor-rt-1")
    resource = Resource(id="resource-rt-1")
    actor.label = "Registered Actor"
    resource.kind = "material"

    world.register_object(actor)
    world.register_object(resource)

    restored = World.from_dict(world.to_dict())

    restored_actor = restored.model_registry.get("actor-rt-1")
    restored_resource = restored.model_registry.get(
        "resource-rt-1"
    )

    assert isinstance(restored_actor, Actor)
    assert isinstance(restored_resource, Resource)
    assert restored_actor is not None
    assert restored_actor.label == "Registered Actor"
    assert restored_resource is not None
    assert restored_resource.kind == "material"

    restored.enable_authority_mode("secret")
    try:
        with pytest.raises(PermissionError):
            restored_actor.attributes["label"] = "forbidden"
    finally:
        restored.disable_authority_mode()


def test_world_from_dict_null_optional_maps_defaults_empty():
    """World.from_dict should handle null optional maps and graph payloads."""
    world = World.from_dict(
        {
            "id": "w-null",
            "attributes": None,
            "relations": None,
            "state": None,
            "context": None,
            "provenance": None,
            "space_object_graph": None,
            "space_relation_graph": None,
        }
    )

    assert world.attributes.get("kind") == "world"
    assert world.relations == {}
    assert world.state == {}
    assert world.context == {}
    assert world.provenance == {}
    assert world.space_object_graph.spaces == {}
    assert world.space_relation_graph.relations == []
