"""Tests for masm.model.actors."""

import pytest

from masm.model.actors import (
    Actor,
    detect_composition_cycle,
    find_parent_composites,
    resolve_component_tree,
)
from masm.model.registry import WorldModelRegistry


def test_actor_instantiation():
    """Verify that an actor instantiates and receives default attributes."""
    actor = Actor(id="actor-1")

    assert actor.id == "actor-1"
    assert actor.object_type == "actor"
    assert actor.roles == []


def test_actor_add_role_and_tag():
    """Verify that we can enrich an actor with a role and a tag."""
    actor = Actor(id="actor-1")

    actor.add_role("leader")
    actor.add_tag("human")

    assert "leader" in actor.roles
    assert "human" in actor.tags


def test_actor_from_dict_null_optional_maps_defaults_empty():
    """Actor should accept null optional maps in from_dict."""
    actor = Actor.from_dict(
        {"id": "a-null", "attributes": None, "relations": None}
    )

    assert isinstance(actor.attributes, dict)
    assert actor.relations == {}


# ---------------------------------------------------------------------------
# Composition mode properties
# ---------------------------------------------------------------------------


def test_actor_composition_mode_defaults_standalone():
    actor = Actor(id="a-1")
    assert actor.composition_mode == "standalone"
    assert not actor.is_composite
    assert not actor.is_collective


def test_actor_is_composite_true_when_mode_composite():
    actor = Actor(id="a-1")
    actor.composition_mode = "composite"
    assert actor.is_composite
    assert not actor.is_collective


def test_actor_is_collective_true_when_mode_collective():
    actor = Actor(id="a-1")
    actor.composition_mode = "collective"
    assert actor.is_collective
    assert not actor.is_composite


def test_get_components_returns_empty_for_non_composite():
    actor = Actor(id="a-1")
    assert actor.get_components() == []


def test_get_components_returns_linked_ids():
    actor = Actor(id="a-1")
    actor.composition_mode = "composite"
    actor.add_component("a-2")
    actor.add_component("a-3")
    assert sorted(actor.get_components()) == ["a-2", "a-3"]


# ---------------------------------------------------------------------------
# add_component guard
# ---------------------------------------------------------------------------


def test_add_component_requires_composite_mode():
    actor = Actor(id="a-1")
    with pytest.raises(ValueError, match="composition_mode"):
        actor.add_component("a-2")


def test_add_component_collective_mode_raises():
    actor = Actor(id="a-1")
    actor.composition_mode = "collective"
    with pytest.raises(ValueError, match="composition_mode"):
        actor.add_component("a-2")


def test_add_component_succeeds_in_composite_mode():
    actor = Actor(id="a-1")
    actor.composition_mode = "composite"
    actor.add_component("a-2")
    assert "a-2" in actor.get_components()


def test_remove_component_removes_relation():
    actor = Actor(id="a-1")
    actor.composition_mode = "composite"
    actor.add_component("a-2")
    actor.remove_component("a-2")
    assert actor.get_components() == []


# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------


def _make_registry(*actors: Actor) -> WorldModelRegistry:
    reg = WorldModelRegistry()
    for a in actors:
        reg.register(a)
    return reg


def test_detect_composition_cycle_no_cycle():
    a1 = Actor(id="a-1")
    a2 = Actor(id="a-2")
    a1.composition_mode = "composite"
    reg = _make_registry(a1, a2)
    assert not detect_composition_cycle("a-1", "a-2", reg)


def test_detect_composition_cycle_direct_self_loop():
    a1 = Actor(id="a-1")
    reg = _make_registry(a1)
    # Adding a-1 as its own component would be a cycle
    assert detect_composition_cycle("a-1", "a-1", reg)


def test_detect_composition_cycle_direct():
    # a1 → a2; trying to add a1 as component of a2 would cycle
    a1 = Actor(id="a-1")
    a2 = Actor(id="a-2")
    a1.composition_mode = "composite"
    a1.add_component("a-2")
    reg = _make_registry(a1, a2)
    assert detect_composition_cycle("a-2", "a-1", reg)


def test_detect_composition_cycle_transitive():
    # a1 → a2 → a3; trying to add a1 as component of a3 would cycle
    a1 = Actor(id="a-1")
    a2 = Actor(id="a-2")
    a3 = Actor(id="a-3")
    a1.composition_mode = "composite"
    a2.composition_mode = "composite"
    a1.add_component("a-2")
    a2.add_component("a-3")
    reg = _make_registry(a1, a2, a3)
    assert detect_composition_cycle("a-3", "a-1", reg)


def test_detect_composition_cycle_no_false_positive():
    # a1 → a2, a1 → a3 (sibling), adding a4 to a3 is safe
    a1 = Actor(id="a-1")
    a2 = Actor(id="a-2")
    a3 = Actor(id="a-3")
    a4 = Actor(id="a-4")
    a1.composition_mode = "composite"
    a3.composition_mode = "composite"
    a1.add_component("a-2")
    a1.add_component("a-3")
    reg = _make_registry(a1, a2, a3, a4)
    assert not detect_composition_cycle("a-3", "a-4", reg)


# ---------------------------------------------------------------------------
# resolve_component_tree
# ---------------------------------------------------------------------------


def test_resolve_component_tree_flat():
    a1 = Actor(id="a-1")
    a2 = Actor(id="a-2")
    a3 = Actor(id="a-3")
    a1.composition_mode = "composite"
    a1.add_component("a-2")
    a1.add_component("a-3")
    reg = _make_registry(a1, a2, a3)
    tree = resolve_component_tree("a-1", reg)
    assert tree == {"a-1": {"a-2": {}, "a-3": {}}}


def test_resolve_component_tree_nested():
    a1 = Actor(id="a-1")
    a2 = Actor(id="a-2")
    a3 = Actor(id="a-3")
    a1.composition_mode = "composite"
    a2.composition_mode = "composite"
    a1.add_component("a-2")
    a2.add_component("a-3")
    reg = _make_registry(a1, a2, a3)
    tree = resolve_component_tree("a-1", reg)
    assert tree == {"a-1": {"a-2": {"a-3": {}}}}


def test_resolve_component_tree_missing_node_returns_empty():
    a1 = Actor(id="a-1")
    a1.composition_mode = "composite"
    a1.add_component("a-ghost")
    reg = _make_registry(a1)
    tree = resolve_component_tree("a-1", reg)
    assert tree == {"a-1": {"a-ghost": {}}}


def test_resolve_component_tree_standalone_is_empty():
    a1 = Actor(id="a-1")
    reg = _make_registry(a1)
    tree = resolve_component_tree("a-1", reg)
    assert tree == {"a-1": {}}


# ---------------------------------------------------------------------------
# find_parent_composites
# ---------------------------------------------------------------------------


def test_find_parent_composites_single_parent():
    a1 = Actor(id="a-1")
    a2 = Actor(id="a-2")
    a1.composition_mode = "composite"
    a1.add_component("a-2")
    reg = _make_registry(a1, a2)
    assert find_parent_composites("a-2", reg) == ["a-1"]


def test_find_parent_composites_multiple_parents():
    a1 = Actor(id="a-1")
    a2 = Actor(id="a-2")
    shared = Actor(id="shared")
    a1.composition_mode = "composite"
    a2.composition_mode = "composite"
    a1.add_component("shared")
    a2.add_component("shared")
    reg = _make_registry(a1, a2, shared)
    assert find_parent_composites("shared", reg) == [
        "a-1",
        "a-2",
    ]


def test_find_parent_composites_no_parent():
    a1 = Actor(id="a-1")
    reg = _make_registry(a1)
    assert find_parent_composites("a-1", reg) == []


# ---------------------------------------------------------------------------
# Serialisation round-trip with components
# ---------------------------------------------------------------------------


def test_actor_serialization_round_trip_with_components():
    actor = Actor(id="a-1")
    actor.composition_mode = "composite"
    actor.add_component("a-2")
    actor.add_component("a-3")
    restored = Actor.from_dict(actor.to_dict())
    assert restored.composition_mode == "composite"
    assert sorted(restored.get_components()) == ["a-2", "a-3"]
