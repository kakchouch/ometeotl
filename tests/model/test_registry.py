"""Tests for masm.model.registry (WorldModelRegistry, MinimalModelRegistry, reconstruct_model_object)."""

import pytest

from masm.model.actors import Actor
from masm.model.goals import Goal
from masm.model.registry import (
    MinimalModelRegistry,
    WorldModelRegistry,
    reconstruct_model_object,
)
from masm.model.resources import Resource
from masm.model.spaces import Space

# ---------------------------------------------------------------------------
# WorldModelRegistry
# ---------------------------------------------------------------------------


def test_world_registry_register_and_exists():
    """Registered object is reported as existing."""
    registry = WorldModelRegistry()
    actor = Actor(id="actor-reg-1")
    registry.register(actor)
    assert registry.exists("actor-reg-1") is True
    assert registry.exists("unknown") is False


def test_world_registry_get_returns_registered_object():
    """get() returns the exact registered object."""
    registry = WorldModelRegistry()
    space = Space(id="space-reg-1")
    registry.register(space)
    assert registry.get("space-reg-1") is space
    assert registry.get("missing") is None


def test_world_registry_unregister_removes_object():
    """Unregistered ID is no longer present in the registry."""
    registry = WorldModelRegistry()
    actor = Actor(id="actor-reg-2")
    registry.register(actor)
    registry.unregister("actor-reg-2")
    assert registry.exists("actor-reg-2") is False


def test_world_registry_unregister_missing_id_is_noop():
    """Unregistering an unknown ID does not raise."""
    registry = WorldModelRegistry()
    registry.unregister("nonexistent")  # should not raise


def test_world_registry_duplicate_id_raises():
    """Registering a different object under an existing ID raises ValueError."""
    registry = WorldModelRegistry()
    registry.register(Actor(id="actor-dup"))
    with pytest.raises(
        ValueError, match="Duplicate model object id"
    ):
        registry.register(Actor(id="actor-dup"))


def test_world_registry_same_object_re_registration_is_noop():
    """Re-registering the exact same object instance is a no-op."""
    registry = WorldModelRegistry()
    actor = Actor(id="actor-same")
    registry.register(actor)
    registry.register(actor)  # should not raise


def test_world_registry_all_ids_returns_sorted():
    """all_ids() returns sorted IDs regardless of insertion order."""
    registry = WorldModelRegistry()
    registry.register(Actor(id="zzz"))
    registry.register(Actor(id="aaa"))
    registry.register(Space(id="mmm"))
    assert registry.all_ids() == ["aaa", "mmm", "zzz"]


def test_world_registry_clear_removes_all_objects():
    """clear() empties the registry."""
    registry = WorldModelRegistry()
    registry.register(Actor(id="actor-clr"))
    registry.clear()
    assert registry.exists("actor-clr") is False
    assert registry.all_ids() == []


def test_world_registry_mutation_guard_raises_on_unauthorized_mutation():
    """Mutation guard callback is invoked on register; raises blocks the mutation."""
    registry = WorldModelRegistry()

    def strict_guard(token):
        raise PermissionError("mutation not allowed")

    registry.set_mutation_guard(strict_guard)
    with pytest.raises(
        PermissionError, match="mutation not allowed"
    ):
        registry.register(Actor(id="blocked"))


def test_world_registry_mutation_guard_authorised_token_passes():
    """Mutation guard callback that accepts the right token allows mutation."""
    registry = WorldModelRegistry()
    allowed_token = "authority-token"

    def lenient_guard(token):
        if token != allowed_token:
            raise PermissionError("bad token")

    registry.set_mutation_guard(lenient_guard)
    registry.register(
        Actor(id="guarded-actor"), authority_token=allowed_token
    )
    assert registry.exists("guarded-actor") is True


def test_world_registry_round_trip_serialization():
    """Registry can be serialized and reconstructed deterministically."""
    registry = WorldModelRegistry()
    registry.register(Actor(id="actor-serial"))
    registry.register(Space(id="space-serial"))

    payload = registry.to_dict()
    restored = WorldModelRegistry.from_dict(payload)

    assert restored.to_dict() == payload
    assert restored.exists("actor-serial") is True
    assert restored.exists("space-serial") is True


# ---------------------------------------------------------------------------
# MinimalModelRegistry
# ---------------------------------------------------------------------------


def test_minimal_registry_register_and_exists():
    """Registered object is reported as existing in MinimalModelRegistry."""
    MinimalModelRegistry.clear()
    actor = Actor(id="minimal-actor-1")
    MinimalModelRegistry.register(actor)
    assert MinimalModelRegistry.exists("minimal-actor-1") is True
    MinimalModelRegistry.clear()


def test_minimal_registry_duplicate_id_raises():
    """Registering a different object under an existing ID raises with the correct message."""
    MinimalModelRegistry.clear()
    MinimalModelRegistry.register(Resource(id="res-dup"))
    with pytest.raises(
        ValueError, match="Duplicate model object id: res-dup"
    ):
        MinimalModelRegistry.register(Resource(id="res-dup"))
    MinimalModelRegistry.clear()


def test_minimal_registry_clear_isolates_tests():
    """clear() removes all global state from MinimalModelRegistry."""
    MinimalModelRegistry.register(Actor(id="isolation-actor"))
    MinimalModelRegistry.clear()
    assert (
        MinimalModelRegistry.exists("isolation-actor") is False
    )


def test_minimal_registry_does_not_share_state_with_world_registry():
    """MinimalModelRegistry and WorldModelRegistry are fully isolated."""
    MinimalModelRegistry.clear()
    world_registry = WorldModelRegistry()
    actor = Actor(id="isolation-check")
    world_registry.register(actor)

    assert (
        MinimalModelRegistry.exists("isolation-check") is False
    )
    MinimalModelRegistry.clear()


# ---------------------------------------------------------------------------
# reconstruct_model_object
# ---------------------------------------------------------------------------


def test_reconstruct_model_object_actor():
    """reconstruct_model_object round-trips an Actor."""
    actor = Actor(id="reconstruct-actor")
    payload = actor.to_dict()
    restored = reconstruct_model_object(payload)
    assert restored.to_dict() == payload


def test_reconstruct_model_object_space():
    """reconstruct_model_object round-trips a Space."""
    space = Space(id="reconstruct-space")
    payload = space.to_dict()
    restored = reconstruct_model_object(payload)
    assert restored.to_dict() == payload


def test_reconstruct_model_object_goal():
    """reconstruct_model_object round-trips a Goal via default registry dispatch."""
    goal = Goal(
        id="reconstruct-goal",
        actor_id="actor-1",
        kind="final",
        target_condition={"safety": 1.0},
    )
    payload = goal.to_dict()
    restored = reconstruct_model_object(payload)

    assert isinstance(restored, Goal)
    assert restored.to_dict() == payload


def test_reconstruct_model_object_custom_factory():
    """Custom factories override the default lookup."""
    actor = Actor(id="custom-factory-actor")
    payload = actor.to_dict()

    sentinel = {"called": False}

    def custom_factory(raw):
        sentinel["called"] = True
        return Actor.from_dict(raw)

    reconstruct_model_object(
        payload, object_factories={"actor": custom_factory}
    )
    assert sentinel["called"] is True


def test_reconstruct_model_object_default_factories_cached():
    """Default factories are reused across calls (cache is consistent)."""
    from masm.model import registry as reg_module

    # Prime the cache
    reg_module._DEFAULT_FACTORIES = None
    reg_module._get_default_factories()
    first = reg_module._DEFAULT_FACTORIES

    reg_module._get_default_factories()
    second = reg_module._DEFAULT_FACTORIES

    assert first is second
