"""Tests for masm.model.actors."""

from masm.model.actors import Actor


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
    actor = Actor.from_dict({"id": "a-null", "attributes": None, "relations": None})

    assert isinstance(actor.attributes, dict)
    assert actor.relations == {}
