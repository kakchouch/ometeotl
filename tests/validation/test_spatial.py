"""Tests for masm.validation.spatial."""

from masm.model.actions import Action
from masm.model.actors import Actor
from masm.model.spaces import Space
from masm.model.world import World
from masm.validation.base import ValidationContext
from masm.validation.spatial import SpatialValidator


def _build_world() -> World:
    world = World(id="world-1")
    world.add_space(Space(id="space-1"))
    world.register_object(Actor(id="actor-1"))
    world.place_object("actor-1", "space-1")
    return world


def test_spatial_validator_accepts_actor_in_space():
    """Actor placed in known space should pass spatial validation."""
    world = _build_world()
    action = Action(
        id="a-1",
        actor_id="actor-1",
        world_id="world-1",
        space_id="space-1",
        action_type="move",
    )

    result = SpatialValidator().validate(
        action, ValidationContext(metadata={"world": world})
    )

    assert result.valid is True


def test_spatial_validator_rejects_unknown_space():
    """Unknown space references should be rejected."""
    world = _build_world()
    action = Action(
        id="a-2",
        actor_id="actor-1",
        world_id="world-1",
        space_id="space-missing",
        action_type="move",
    )

    result = SpatialValidator().validate(
        action, ValidationContext(metadata={"world": world})
    )

    assert result.valid is False
    assert result.errors[0].code == "SPATIAL-UNKNOWN-SPACE"
