"""Core authority/runtime tests for ometeotl/MASM."""

import pytest

from masm.core.authority import AuthorityCommandHandler, CommandEnvelope
from masm.core.runtime import build_runtime
from masm.model.actors import Actor
from masm.model.resources import Resource
from masm.model.spaces import Space
from masm.model.world import World


def test_world_authority_mode_blocks_direct_mutations():
    """Direct mutations are blocked when authority mode is enabled."""
    world = World(id="world-auth-1")
    world.enable_authority_mode("secret")

    with pytest.raises(PermissionError):
        world.add_space(Space(id="forbidden"))


def test_world_authority_mode_allows_authorized_mutations():
    """Mutations succeed with the expected authority token."""
    world = World(id="world-auth-2")
    world.enable_authority_mode("secret")
    world.add_space(Space(id="allowed"), authority_token="secret")

    assert world.get_space("allowed") is not None


def test_world_local_mode_mutations_do_not_require_authority_token():
    """Local/in-process usage keeps direct mutation behavior by default."""
    world = World(id="world-local-1")
    world.add_space(Space(id="local-zone"))
    world.place_object("actor-local", "local-zone")

    assert world.get_space("local-zone") is not None
    assert "actor-local" in world.space_object_graph.list_objects_in_space("local-zone")


def test_authority_handler_applies_allowlisted_commands():
    """Allowlisted commands are accepted via the authority boundary."""
    world = World(id="world-cmd-1")
    handler = AuthorityCommandHandler(world)
    try:
        add_space_result = handler.submit(
            CommandEnvelope(
                command_id="c-1",
                actor_id="system",
                command_type="add_space",
                sequence=1,
                payload={"space": Space(id="zone-1").to_dict()},
            )
        )
        assert add_space_result.accepted is True

        place_result = handler.submit(
            CommandEnvelope(
                command_id="c-2",
                actor_id="system",
                command_type="place_object",
                sequence=2,
                payload={"object_id": "actor-42", "space_id": "zone-1"},
            )
        )
        assert place_result.accepted is True
    finally:
        handler.close()

    assert "actor-42" in world.space_object_graph.list_objects_in_space("zone-1")


def test_authority_handler_rejects_unknown_actor():
    """Unknown actors are rejected before command application."""
    world = World(id="world-cmd-2")
    world.register_object(Actor(id="actor-known"))
    handler = AuthorityCommandHandler(world)
    try:
        result_unknown = handler.submit(
            CommandEnvelope(
                command_id="c-3",
                actor_id="actor-unknown",
                command_type="add_space",
                sequence=1,
                payload={"space": Space(id="zone-2").to_dict()},
            )
        )
        assert result_unknown.accepted is False

        result_known = handler.submit(
            CommandEnvelope(
                command_id="c-4",
                actor_id="actor-known",
                command_type="add_space",
                sequence=1,
                payload={"space": Space(id="zone-3").to_dict()},
            )
        )
        assert result_known.accepted is True
    finally:
        handler.close()
        world.unregister_object("actor-known")


def test_authority_handler_rejects_duplicate_and_out_of_order_sequence():
    """Idempotency and sequence ordering are enforced."""
    world = World(id="world-cmd-3")
    handler = AuthorityCommandHandler(world)
    try:
        first = handler.submit(
            CommandEnvelope(
                command_id="c-5",
                actor_id="system",
                command_type="add_space",
                sequence=1,
                payload={"space": Space(id="zone-4").to_dict()},
            )
        )
        duplicate = handler.submit(
            CommandEnvelope(
                command_id="c-5",
                actor_id="system",
                command_type="add_space",
                sequence=2,
                payload={"space": Space(id="zone-5").to_dict()},
            )
        )
        out_of_order = handler.submit(
            CommandEnvelope(
                command_id="c-6",
                actor_id="system",
                command_type="add_space",
                sequence=1,
                payload={"space": Space(id="zone-6").to_dict()},
            )
        )
    finally:
        handler.close()

    assert first.accepted is True
    assert duplicate.accepted is False
    assert out_of_order.accepted is False


def test_authority_handler_close_restores_local_mutations():
    """Closing the handler removes the lock so local app flows continue to work."""
    world = World(id="world-cmd-4")
    handler = AuthorityCommandHandler(world)
    handler.close()

    world.add_space(Space(id="zone-after-close"))
    assert world.get_space("zone-after-close") is not None


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

    with build_runtime(world, server_authoritative=True) as runtime:
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
    assert world.get_space("zone-cm-open-after-exception") is not None


def test_authority_handler_rejects_global_registry_bypass():
    """Global registry writes do not satisfy authoritative actor checks."""
    from masm.model.registry import MinimalModelRegistry

    MinimalModelRegistry.clear()
    MinimalModelRegistry.register(Actor(id="global-only-actor"))

    world = World(id="world-cmd-5")
    handler = AuthorityCommandHandler(world)
    try:
        result = handler.submit(
            CommandEnvelope(
                command_id="c-7",
                actor_id="global-only-actor",
                command_type="add_space",
                sequence=1,
                payload={"space": Space(id="zone-7").to_dict()},
            )
        )
        assert result.accepted is False
    finally:
        handler.close()
        MinimalModelRegistry.clear()


def test_world_model_registry_direct_mutation_blocked_in_authority_mode():
    """Direct model_registry mutation is blocked when authority mode is enabled."""
    world = World(id="world-cmd-9")
    handler = AuthorityCommandHandler(world)
    try:
        with pytest.raises(PermissionError):
            world.model_registry.register(Actor(id="actor-direct-bypass"))
    finally:
        handler.close()


def test_unregistered_actor_id_does_not_reset_sequence_history():
    """Sequence history must survive unregister/register cycles for same actor ID."""
    world = World(id="world-cmd-10")
    world.register_object(Actor(id="actor-reuse"))
    handler = AuthorityCommandHandler(world)
    try:
        first = handler.submit(
            CommandEnvelope(
                command_id="c-14",
                actor_id="actor-reuse",
                command_type="add_space",
                sequence=5,
                payload={"space": Space(id="zone-14").to_dict()},
            )
        )
        unregister = handler.submit(
            CommandEnvelope(
                command_id="c-15",
                actor_id="system",
                command_type="unregister_object",
                sequence=1,
                payload={"object_id": "actor-reuse"},
            )
        )
        register_again = handler.submit(
            CommandEnvelope(
                command_id="c-16",
                actor_id="system",
                command_type="register_object",
                sequence=2,
                payload={"object": {"id": "actor-reuse", "object_type": "actor"}},
            )
        )
        replay = handler.submit(
            CommandEnvelope(
                command_id="c-17",
                actor_id="actor-reuse",
                command_type="add_space",
                sequence=2,
                payload={"space": Space(id="zone-15").to_dict()},
            )
        )
    finally:
        handler.close()

    assert first.accepted is True
    assert unregister.accepted is True
    assert register_again.accepted is True
    assert replay.accepted is False


def test_authority_handler_supports_custom_command_handlers():
    """Custom command handlers can be registered without subclassing."""

    def custom_ping_handler(command, world, authority_token):
        return {
            "echo": str(command.payload.get("value") or ""),
            "world_id": world.id,
            "token_used": bool(authority_token),
        }

    world = World(id="world-cmd-11")
    world.register_object(Actor(id="actor-custom"))
    handler = AuthorityCommandHandler(
        world,
        custom_command_handlers={"custom_ping": custom_ping_handler},
    )
    try:
        result = handler.submit(
            CommandEnvelope(
                command_id="c-18",
                actor_id="actor-custom",
                command_type="custom_ping",
                sequence=1,
                payload={"value": "pong"},
            )
        )
    finally:
        handler.close()

    assert result.accepted is True
    assert result.applied == {
        "echo": "pong",
        "world_id": "world-cmd-11",
        "token_used": True,
    }


def test_authority_handler_register_object_preserves_concrete_subtypes():
    """Authority registration keeps actor/resource concrete runtime types."""
    world = World(id="world-cmd-13")
    handler = AuthorityCommandHandler(world)
    try:
        register_actor = handler.submit(
            CommandEnvelope(
                command_id="c-22",
                actor_id="system",
                command_type="register_object",
                sequence=1,
                payload={
                    "object": {
                        "id": "actor-poly",
                        "object_type": "actor",
                        "attributes": {"roles": ["leader"]},
                    }
                },
            )
        )
        register_resource = handler.submit(
            CommandEnvelope(
                command_id="c-23",
                actor_id="system",
                command_type="register_object",
                sequence=2,
                payload={
                    "object": {
                        "id": "resource-poly",
                        "object_type": "resource",
                        "attributes": {"resource_mode": "flow"},
                    }
                },
            )
        )
    finally:
        handler.close()

    actor_obj = world.model_registry.get("actor-poly")
    resource_obj = world.model_registry.get("resource-poly")

    assert register_actor.accepted is True
    assert register_resource.accepted is True
    assert isinstance(actor_obj, Actor)
    assert isinstance(resource_obj, Resource)
    assert actor_obj.roles == ["leader"]
    assert resource_obj.resource_mode == "flow"


def test_command_envelope_from_dict_rejects_invalid_sequence_values():
    """Deserialization reports invalid sequence values explicitly."""
    with pytest.raises(ValueError):
        CommandEnvelope.from_dict(
            {
                "command_id": "cx-1",
                "actor_id": "a-1",
                "command_type": "add_space",
                "sequence": "not-an-int",
            }
        )


def test_authority_handler_tracker_capacity_rejects_new_actor_without_reset():
    """Tracker capacity rejects new actors instead of evicting old actor state."""
    world = World(id="world-cmd-8")
    world.register_object(Actor(id="actor-a"))
    world.register_object(Actor(id="actor-b"))
    handler = AuthorityCommandHandler(world, sequence_tracker_max_actors=1)
    try:
        accepted_a = handler.submit(
            CommandEnvelope(
                command_id="c-11",
                actor_id="actor-a",
                command_type="add_space",
                sequence=1,
                payload={"space": Space(id="zone-11").to_dict()},
            )
        )
        rejected_b = handler.submit(
            CommandEnvelope(
                command_id="c-12",
                actor_id="actor-b",
                command_type="add_space",
                sequence=1,
                payload={"space": Space(id="zone-12").to_dict()},
            )
        )
        replay_a = handler.submit(
            CommandEnvelope(
                command_id="c-13",
                actor_id="actor-a",
                command_type="add_space",
                sequence=1,
                payload={"space": Space(id="zone-13").to_dict()},
            )
        )
    finally:
        handler.close()

    assert accepted_a.accepted is True
    assert rejected_b.accepted is False
    assert replay_a.accepted is False


def test_authority_handler_tracker_capacity_ignores_unregistered_actors():
    """Bounded tracker should admit new active actors after churn."""
    world = World(id="world-cmd-12")
    world.register_object(Actor(id="actor-a"))
    world.register_object(Actor(id="actor-b"))
    handler = AuthorityCommandHandler(world, sequence_tracker_max_actors=1)
    try:
        accepted_a = handler.submit(
            CommandEnvelope(
                command_id="c-19",
                actor_id="actor-a",
                command_type="add_space",
                sequence=1,
                payload={"space": Space(id="zone-16").to_dict()},
            )
        )
        unregistered_a = handler.submit(
            CommandEnvelope(
                command_id="c-20",
                actor_id="system",
                command_type="unregister_object",
                sequence=1,
                payload={"object_id": "actor-a"},
            )
        )
        accepted_b = handler.submit(
            CommandEnvelope(
                command_id="c-21",
                actor_id="actor-b",
                command_type="add_space",
                sequence=1,
                payload={"space": Space(id="zone-17").to_dict()},
            )
        )
    finally:
        handler.close()

    assert accepted_a.accepted is True
    assert unregistered_a.accepted is True
    assert accepted_b.accepted is True


def test_authority_handler_uses_bounded_audit_log():
    """Audit log keeps a bounded size to prevent unbounded growth."""
    world = World(id="world-cmd-6")
    handler = AuthorityCommandHandler(world, audit_log_maxlen=2)
    try:
        handler.submit(
            CommandEnvelope(
                command_id="c-8",
                actor_id="system",
                command_type="add_space",
                sequence=1,
                payload={"space": Space(id="zone-8").to_dict()},
            )
        )
        handler.submit(
            CommandEnvelope(
                command_id="c-9",
                actor_id="system",
                command_type="add_space",
                sequence=2,
                payload={"space": Space(id="zone-9").to_dict()},
            )
        )
        handler.submit(
            CommandEnvelope(
                command_id="c-10",
                actor_id="system",
                command_type="add_space",
                sequence=3,
                payload={"space": Space(id="zone-10").to_dict()},
            )
        )
    finally:
        handler.close()

    assert len(handler.audit_log) == 2


def test_authority_handler_rejects_invalid_limit_arguments():
    """Constructor rejects invalid bounded-memory configuration values."""
    world = World(id="world-cmd-7")

    with pytest.raises(ValueError):
        AuthorityCommandHandler(world, audit_log_maxlen=0)

    with pytest.raises(ValueError):
        AuthorityCommandHandler(world, processed_ids_maxlen=0)

    with pytest.raises(ValueError):
        AuthorityCommandHandler(world, sequence_tracker_max_actors=0)
