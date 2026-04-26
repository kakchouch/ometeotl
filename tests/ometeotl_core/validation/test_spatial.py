"""Tests for ometeotl_core.validation.spatial."""

from ometeotl_core.model.actions import Action
from ometeotl_core.model.actors import Actor
from ometeotl_core.model.spaces import Space
from ometeotl_core.model.world import World
from ometeotl_core.validation.base import ValidationContext
from ometeotl_core.validation.spatial import SpatialValidator


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


def test_spatial_validator_skips_when_space_id_is_missing():
    """Spatial validator should be silent for payloads without space context."""
    world = _build_world()
    payload = {"id": "global-object", "actor_id": "actor-1"}

    result = SpatialValidator().validate(
        payload, ValidationContext(metadata={"world": world})
    )

    assert result.valid is True
    assert result.summary["total"] == 0
