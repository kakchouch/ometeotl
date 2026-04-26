"""Tests for ometeotl_core.core.runtime."""

import pytest

from ometeotl_core.generic.authority import CommandEnvelope
from ometeotl_core.generic.runtime import build_runtime
from ometeotl_core.model.actors import Actor
from ometeotl_core.model.spaces import Space
from ometeotl_core.model.world import World
from ometeotl_core.validation import LEVEL_FULL, PROFILE_ENFORCE_STRUCTURE


def test_build_runtime_local_mode_keeps_world_unlocked():
    """Runtime bootstrap does not lock world unless server flag is enabled."""
    world = World(id="world-runtime-local-1")
    runtime = build_runtime(world, server_authoritative=False)

    assert runtime.authoritative is False
    world.add_space(Space(id="zone-local-runtime"))
    assert world.get_space("zone-local-runtime") is not None


def test_build_runtime_server_mode_locks_then_unlocks_on_close():
    """Server runtime enables lock; close restores local direct access."""
    world = World(id="world-runtime-server-1")
    runtime = build_runtime(world, server_authoritative=True)

    assert runtime.authoritative is True
    with pytest.raises(PermissionError):
        world.add_space(Space(id="zone-blocked-runtime"))

    runtime.close()
    world.add_space(Space(id="zone-open-runtime"))
    assert world.get_space("zone-open-runtime") is not None


def test_runtime_context_manager_releases_lock_on_normal_exit():
    """Using RuntimeContext with 'with' releases authority lock on exit."""
    world = World(id="world-runtime-cm-1")

    with build_runtime(
        world, server_authoritative=True
    ) as runtime:
        assert runtime.authoritative is True
        with pytest.raises(PermissionError):
            world.add_space(Space(id="zone-cm-blocked"))

    world.add_space(Space(id="zone-cm-open"))
    assert world.get_space("zone-cm-open") is not None


def test_runtime_context_manager_releases_lock_on_exception_exit():
    """RuntimeContext must release lock even if an exception occurs in block."""
    world = World(id="world-runtime-cm-2")

    with pytest.raises(RuntimeError):
        with build_runtime(world, server_authoritative=True):
            raise RuntimeError("boom")

    world.add_space(Space(id="zone-cm-open-after-exception"))
    assert (
        world.get_space("zone-cm-open-after-exception")
        is not None
    )


def test_build_runtime_passes_extensibility_hooks():
    """Runtime builder should pass custom handlers and object factories through."""

    def custom_ping(command, world, authority_token):
        return {
            "ok": True,
            "world_id": world.id,
            "used_token": bool(authority_token),
        }

    def custom_actor_factory(payload):
        return Actor(id=str(payload.get("id") or ""))

    world = World(id="world-runtime-ext-1")
    world.register_object(Actor(id="actor-runtime-ext"))

    with build_runtime(
        world,
        server_authoritative=True,
        custom_command_handlers={"custom_ping": custom_ping},
        object_factories={"custom_actor": custom_actor_factory},
    ) as runtime:
        assert runtime.authoritative is True
        assert runtime.authority_handler is not None
        ping_result = runtime.authority_handler.submit(
            CommandEnvelope(
                command_id="rt-ext-1",
                actor_id="actor-runtime-ext",
                command_type="custom_ping",
                sequence=1,
                payload={},
            )
        )
        register_result = runtime.authority_handler.submit(
            CommandEnvelope(
                command_id="rt-ext-2",
                actor_id="system",
                command_type="register_object",
                sequence=1,
                payload={
                    "object": {
                        "id": "actor-runtime-custom",
                        "object_type": "custom_actor",
                    }
                },
            )
        )

    custom_obj = world.model_registry.get("actor-runtime-custom")
    assert ping_result.accepted is True
    assert ping_result.applied == {
        "ok": True,
        "world_id": "world-runtime-ext-1",
        "used_token": True,
    }
    assert register_result.accepted is True
    assert isinstance(custom_obj, Actor)


def test_build_runtime_passes_validation_hardening_options():
    """Runtime builder wires validation hardening controls to authority mode."""
    world = World(id="world-runtime-hard-1")

    with build_runtime(
        world,
        server_authoritative=True,
        validation_policy_profile=PROFILE_ENFORCE_STRUCTURE,
        validation_block_on_error=True,
        validation_completeness_level=LEVEL_FULL,
    ) as runtime:
        assert runtime.authority_handler is not None
        result = runtime.authority_handler.submit(
            CommandEnvelope(
                command_id="rt-hard-1",
                actor_id="system",
                command_type="register_object",
                sequence=1,
                payload={
                    "object": {
                        "id": "actor-runtime-hard-1",
                        "object_type": "actor",
                    }
                },
            )
        )

    assert result.accepted is False
    assert result.reason == "Validation policy rejected command"
    assert result.validation["summary"]["error"] >= 1
    assert (
        world.model_registry.get("actor-runtime-hard-1") is None
    )


def test_build_runtime_soft_gate_off_skips_validation_blocking():
    """Soft-gate off should bypass validation blocking in runtime authority mode."""
    world = World(id="world-runtime-soft-off-1")

    with build_runtime(
        world,
        server_authoritative=True,
        validation_soft_gate=False,
        validation_policy_profile=PROFILE_ENFORCE_STRUCTURE,
        validation_block_on_error=True,
        validation_completeness_level=LEVEL_FULL,
    ) as runtime:
        assert runtime.authority_handler is not None
        result = runtime.authority_handler.submit(
            CommandEnvelope(
                command_id="rt-soft-off-1",
                actor_id="system",
                command_type="register_object",
                sequence=1,
                payload={
                    "object": {
                        "id": "actor-runtime-soft-off-1",
                        "object_type": "actor",
                    }
                },
            )
        )

    assert result.accepted is True
    assert result.validation["summary"]["total"] == 0
    assert (
        world.model_registry.get("actor-runtime-soft-off-1")
        is not None
    )
