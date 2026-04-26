"""Tests for abstract actor behavior in ometeotl_core.model.actors."""

import pytest

from ometeotl_core.model.actors import (
    Actor,
    is_abstract_composite,
    get_concrete_components,
    get_real_world_base,
)
from ometeotl_core.model.registry import WorldModelRegistry
from ometeotl_core.model.spaces import Space
from ometeotl_core.model.world import World


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


def test_is_abstract_composite_in_abstract_space_returns_true():
    """A composite actor placed exclusively in abstract spaces is an abstract composite."""
    a1 = Actor(id="a-1")
    a2 = Actor(id="a-2")
    a1.composition_mode = "composite"
    a1.add_component("a-2")
    reg = _make_registry(a1, a2)
    world = World(id="world-1")
    s1 = Space(id="s-1")
    s1.is_abstract = True
    world.add_space(s1)
    world.place_object("a-1", "s-1")

    assert is_abstract_composite(a1, reg, world) is True


def test_is_abstract_composite_in_non_abstract_space_returns_false():
    """A composite actor placed in a non-abstract space is not an abstract composite."""
    a1 = Actor(id="a-1")
    a2 = Actor(id="a-2")
    a1.composition_mode = "composite"
    a1.add_component("a-2")
    reg = _make_registry(a1, a2)
    world = World(id="world-1")
    s1 = Space(id="s-1")
    s1.is_abstract = False
    world.add_space(s1)
    world.place_object("a-1", "s-1")

    assert is_abstract_composite(a1, reg, world) is False


def test_is_abstract_composite_not_placed_returns_false():
    """A composite actor not placed in any space is not an abstract composite."""
    a1 = Actor(id="a-1")
    a2 = Actor(id="a-2")
    a1.composition_mode = "composite"
    a1.add_component("a-2")
    reg = _make_registry(a1, a2)
    world = World(id="world-1")

    assert is_abstract_composite(a1, reg, world) is False


def test_get_concrete_components_filters_real_world():
    """get_concrete_components returns only non-abstract components."""
    a1 = Actor(id="a-1")
    a2 = Actor(id="a-2")
    a3 = Actor(id="a-3")
    a1.composition_mode = "composite"
    a1.add_component("a-2")
    a1.add_component("a-3")
    reg = _make_registry(a1, a2, a3)
    world = World(id="world-1")

    concrete = get_concrete_components("a-1", reg, world)
    assert sorted(concrete) == ["a-2", "a-3"]


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
    s1 = Space(id="s-1")
    s1.is_abstract = True
    world.add_space(s1)
    world.place_object("a-1", "s-1")

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
    s1 = Space(id="s-1")
    s1.is_abstract = True
    world.add_space(s1)
    world.place_object("a-1", "s-1")
    world.place_object("a-2", "s-1")

    base = get_real_world_base("a-1", reg, world)
    assert sorted(base) == ["a-3", "a-4"]
