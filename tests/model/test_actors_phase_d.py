"""Tests for masm.model.actors - Phase D abstract actor tests."""

import pytest

from masm.model.actors import (
    Actor,
    is_abstract_composite,
    get_abstract_components,
    get_real_world_base,
)
from masm.model.registry import WorldModelRegistry
from masm.model.world import World


def _make_registry(*actors: Actor) -> WorldModelRegistry:
    reg = WorldModelRegistry()
    for a in actors:
        reg.register(a)
    return reg


def test_is_abstract_composite_non_composite_returns_false():
    """A standalone actor is not an abstract composite."""
    a1 = Actor(id="a-1")
    reg = _make_registry(a1)
    world = World(id="world-1")

    assert is_abstract_composite(a1, reg, world) is False


def test_is_abstract_composite_composite_returns_true():
    """A composite actor with components is considered abstract."""
    a1 = Actor(id="a-1")
    a2 = Actor(id="a-2")
    a1.composition_mode = "composite"
    a1.add_component("a-2")
    reg = _make_registry(a1, a2)
    world = World(id="world-1")

    assert is_abstract_composite(a1, reg, world) is True


def test_get_abstract_components_filters_real_world():
    """get_abstract_components returns only non-abstract components."""
    a1 = Actor(id="a-1")
    a2 = Actor(id="a-2")
    a3 = Actor(id="a-3")
    a1.composition_mode = "composite"
    a1.add_component("a-2")
    a1.add_component("a-3")
    reg = _make_registry(a1, a2, a3)
    world = World(id="world-1")

    real = get_abstract_components("a-1", reg, world)
    assert sorted(real) == ["a-2", "a-3"]


def test_get_real_world_base_flat():
    """get_real_world_base with flat hierarchy returns all leaves."""
    a1 = Actor(id="a-1")
    a2 = Actor(id="a-2")
    a3 = Actor(id="a-3")
    a1.composition_mode = "composite"
    a1.add_component("a-2")
    a1.add_component("a-3")
    reg = _make_registry(a1, a2, a3)
    world = World(id="world-1")

    base = get_real_world_base("a-1", reg, world)
    assert sorted(base) == ["a-2", "a-3"]


def test_get_real_world_base_recursive():
    """get_real_world_base recurses through abstract hierarchy."""
    a1 = Actor(id="a-1")
    a2 = Actor(id="a-2")
    a3 = Actor(id="a-3")
    a4 = Actor(id="a-4")
    a1.composition_mode = "composite"
    a2.composition_mode = "composite"
    a1.add_component("a-2")
    a2.add_component("a-3")
    a2.add_component("a-4")
    reg = _make_registry(a1, a2, a3, a4)
    world = World(id="world-1")

    base = get_real_world_base("a-1", reg, world)
    assert sorted(base) == ["a-3", "a-4"]
