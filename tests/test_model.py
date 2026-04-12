# test/test_model.py
# ============================================================
# Basic tests for Ometeotl / MASM core model
#
# Objectives:
# - Verify that package imports work correctly;
# - Verify that base objects instantiate properly;
# - Verify basic behaviors consistent with V1.
# ============================================================
"""
Basic tests for ometeotl/MASM/model.
Objectives:
- Verify that package imports work correctly
- Verify that base objects instantiate properly
- Verify basic behaviors consistent with V1
"""

import pytest

# Import classes from the new packaged architecture.
# MODIFICATION: We now import from "masm.model..."
from masm.model.base import ModelObject
from masm.model.objects import GenericObject
from masm.model.actors import Actor
from masm.model.resources import Resource
from masm.model.spaces import Space, SpaceObjectGraph, SpaceObjectMembership
from masm.model.space_relations import SpaceRelation, SpaceRelationGraph
from masm.model.world import World
from masm.model.perception import (
    Perception,
    PerceivedSpace,
    PerceivedMembership,
    PerceivedRelation,
    VALID_EPISTEMIC_STATUSES,
)
from masm.model.sensor import (
    Sensor,
    CoverageRule,
    NoiseRule,
    TotalCoverageRule,
    IdentityNoiseRule,
)
from masm.model.actions import Action, ActionPrerequisite, ResourceEffect
from masm.core.authority import AuthorityCommandHandler, CommandEnvelope
from masm.core.runtime import build_runtime


def test_model_object_instantiation():
    """
    Verify that the base model object instantiates correctly.
    """
    obj = ModelObject(id="obj-1", object_type="generic")

    assert obj.id == "obj-1"
    assert obj.object_type == "generic"
    assert isinstance(obj.attributes, dict)
    assert isinstance(obj.relations, dict)
    assert isinstance(obj.state, dict)
    assert isinstance(obj.context, dict)
    assert isinstance(obj.provenance, dict)


def test_model_object_add_relation():
    """
    Verify that a simple relation can be added without duplicates.
    """
    obj = ModelObject(id="obj-1", object_type="generic")

    obj.add_relation("linkedto", "obj-2")
    obj.add_relation("linkedto", "obj-2")  # Intentional duplicate

    assert "linkedto" in obj.relations
    assert obj.relations["linkedto"] == ["obj-2"]


def test_generic_object_label_and_description():
    """
    Verify the minimal behavior of GenericObject.
    """
    obj = GenericObject(id="g-1", object_type="generic")

    obj.label = "Mon objet"
    obj.description = "Description de test"

    assert obj.label == "Mon objet"
    assert obj.description == "Description de test"


def test_actor_instantiation():
    """
    Verify that an actor instantiates and receives default attributes.
    """
    actor = Actor(id="actor-1")

    assert actor.id == "actor-1"
    assert actor.object_type == "actor"
    assert actor.roles == []


def test_actor_add_role_and_tag():
    """
    Verify that we can enrich an actor with a role and a tag.
    """
    actor = Actor(id="actor-1")

    actor.add_role("leader")
    actor.add_tag("human")

    assert "leader" in actor.roles
    assert "human" in actor.tags


def test_resource_instantiation():
    """
    Verify that a resource instantiates with default attributes.
    """
    resource = Resource(id="res-1")

    assert resource.id == "res-1"
    assert resource.object_type == "resource"
    assert resource.resource_mode == "stock"


def test_space_instantiation():
    """
    Verify that a space instantiates correctly.
    """
    space = Space(id="space-1")

    assert space.id == "space-1"
    assert space.object_type == "space"
    assert space.kind == "abstract"
    assert space.tags == []
    assert isinstance(space.dimensions, dict)


def test_world_instantiation():
    """
    Verify that a world instantiates correctly.
    """
    world = World(id="world-0")

    assert world.id == "world-0"
    assert world.object_type == "world"
    assert world.kind == "world"
    assert world.is_root_world == True


def test_space_object_graph_membership():
    """
    Verify that we can add a space to a graph
    then declare an object membership in it.
    """
    graph = SpaceObjectGraph()
    space = Space(id="space-1")

    graph.add_space(space)

    membership = SpaceObjectMembership(
        object_id="actor-1",
        space_id="space-1",
        role="occupies",
    )

    graph.add_object_membership(membership)

    found_spaces = graph.spaces_where_object_exists("actor-1")
    assert len(found_spaces) == 1
    assert found_spaces[0].id == "space-1"


def test_space_relation_graph_adjacency():
    """
    Verify that a symmetric space relation of type adjacent_to
    can be properly recorded.
    """
    graph = SpaceRelationGraph()

    relation = SpaceRelation(
        source_space_id="space-a",
        target_space_id="space-b",
        relation_type="adjacent_to",
    )

    graph.add_relation(relation)

    neighbors_a = graph.neighbors_of("space-a")
    neighbors_b = graph.neighbors_of("space-b")

    assert "space-b" in neighbors_a
    assert "space-a" in neighbors_b


def test_empty_relation_name_raises():
    """
    Verify that a relation without a name is rejected.
    """
    obj = ModelObject(id="obj-1", object_type="generic")

    with pytest.raises(ValueError):
        obj.add_relation("", "obj-2")


def test_empty_target_id_raises():
    """
    Verify that a relation without a target is rejected.
    """
    obj = ModelObject(id="obj-1", object_type="generic")

    with pytest.raises(ValueError):
        obj.add_relation("linkedto", "")


# ============================================================
# World-specific tests
# ============================================================


def test_world_add_subspace():
    """
    Verify that a sub-space can be added to a world and retrieved by ID.
    """
    world = World(id="world-1")
    sub = Space(id="zone-a")

    world.add_space(sub)

    assert world.get_space("zone-a") is sub
    assert world.get_space("zone-b") is None


def test_world_add_duplicate_subspace_raises():
    """
    Verify that adding a sub-space with a duplicate ID raises ValueError.
    """
    world = World(id="world-2")
    sub = Space(id="zone-a")
    world.add_space(sub)

    with pytest.raises(ValueError):
        world.add_space(Space(id="zone-a"))


def test_world_place_object_in_subspace():
    """
    Verify that an object can be placed in a sub-space and the membership
    is correctly recorded.
    """
    world = World(id="world-3")
    sub = Space(id="zone-b")
    world.add_space(sub)
    world.place_object("actor-1", "zone-b", role="occupies")

    members = world.space_object_graph.list_objects_in_space("zone-b")
    assert "actor-1" in members


def test_world_place_object_unknown_space_raises():
    """
    Verify that placing an object in an unknown space raises ValueError.
    """
    world = World(id="world-4")

    with pytest.raises(ValueError):
        world.place_object("actor-1", "nonexistent-space")


def test_world_add_space_relation():
    """
    Verify that a space relation can be added between two sub-spaces.
    """
    from masm.model.space_relations import SpaceRelation

    world = World(id="world-5")
    world.add_space(Space(id="s1"))
    world.add_space(Space(id="s2"))

    world.add_space_relation(
        SpaceRelation(
            source_space_id="s1", target_space_id="s2", relation_type="adjacent_to"
        )
    )

    neighbors = world.space_relation_graph.neighbors_of("s1")
    assert "s2" in neighbors


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


def test_world_register_and_unregister_object():
    """
    Verify that objects can be registered into and removed from the
    minimal registry through the world interface.
    """
    from masm.model.registry import MinimalModelRegistry
    from masm.model.actors import Actor

    MinimalModelRegistry.clear()
    world = World(id="world-6")
    actor = Actor(id="actor-reg-1")

    world.register_object(actor)
    assert MinimalModelRegistry.exists("actor-reg-1")

    world.unregister_object("actor-reg-1")
    assert not MinimalModelRegistry.exists("actor-reg-1")

    MinimalModelRegistry.clear()


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
    from masm.model.registry import MinimalModelRegistry
    from masm.model.actors import Actor

    MinimalModelRegistry.clear()
    world = World(id="world-cmd-2")
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

        MinimalModelRegistry.register(Actor(id="actor-known"))
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
        MinimalModelRegistry.clear()


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

    # Must behave like legacy local flow once authority gateway is shut down.
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


def test_world_to_dict_contains_required_fields():
    """
    Verify that World.to_dict() exports all mandatory canonical fields
    required by spec F-3 plus world-specific graph data.
    """
    world = World(id="world-7")
    d = world.to_dict()

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
    assert required.issubset(d.keys())
    assert d["object_type"] == "world"
    assert d["attributes"]["kind"] == "world"
    assert d["attributes"]["is_root_world"] is True


def test_world_to_dict_roundtrip():
    """
    Verify that a world with sub-spaces, memberships, and space relations
    can be serialized to dict and reconstructed without structural loss (F-29).
    """
    from masm.model.space_relations import SpaceRelation

    world = World(id="world-8")
    world.label = "Test World"
    s1 = Space(id="s1")
    s2 = Space(id="s2")
    world.add_space(s1)
    world.add_space(s2)
    world.place_object("actor-x", "s1", role="occupies")
    world.add_space_relation(
        SpaceRelation(
            source_space_id="s1", target_space_id="s2", relation_type="adjacent_to"
        )
    )

    d = world.to_dict()
    restored = World.from_dict(d)

    assert restored.id == "world-8"
    assert restored.object_type == "world"
    assert restored.kind == "world"
    assert restored.is_root_world is True
    assert restored.label == "Test World"
    assert restored.get_space("s1") is not None
    assert restored.get_space("s2") is not None
    assert "actor-x" in restored.space_object_graph.list_objects_in_space("s1")
    assert "s2" in restored.space_relation_graph.neighbors_of("s1")


def test_world_spaces_where_object_exists():
    """
    Verify that a world can report all sub-spaces where a given object
    is present, including multi-space membership (spec A-3, P-3).
    """
    world = World(id="world-9")
    world.add_space(Space(id="phys"))
    world.add_space(Space(id="info"))
    world.place_object("actor-multi", "phys")
    world.place_object("actor-multi", "info")

    spaces = world.space_object_graph.spaces_where_object_exists("actor-multi")
    space_ids = [s.id for s in spaces]
    assert "phys" in space_ids
    assert "info" in space_ids


# ============================================================
# Perception tests
# ============================================================


def test_perception_instantiation():
    """Perception instantiates with correct defaults."""
    p = Perception(id="perc-1", actor_id="actor-1", source_id="world-1")

    assert p.id == "perc-1"
    assert p.actor_id == "actor-1"
    assert p.source_id == "world-1"
    assert p.schema_version == "1.0"
    assert p.perceived_spaces == {}
    assert p.perceived_memberships == []
    assert p.perceived_relations == []


def test_perceived_space_invalid_epistemic_status_raises():
    """PerceivedSpace rejects an unknown epistemic status."""
    with pytest.raises(ValueError):
        PerceivedSpace(space=Space(id="s1"), epistemic_status="omniscient")


def test_perceived_membership_invalid_epistemic_status_raises():
    """PerceivedMembership rejects an unknown epistemic status."""
    with pytest.raises(ValueError):
        PerceivedMembership(
            membership=SpaceObjectMembership(
                object_id="a", space_id="s", role="occupies"
            ),
            epistemic_status="unknown",
        )


def test_perceived_relation_invalid_epistemic_status_raises():
    """PerceivedRelation rejects an unknown epistemic status."""
    with pytest.raises(ValueError):
        PerceivedRelation(
            relation=SpaceRelation(
                source_space_id="s1",
                target_space_id="s2",
                relation_type="adjacent_to",
            ),
            epistemic_status="maybe",
        )


def test_perceived_space_valid_epistemic_statuses():
    """All documented epistemic statuses are accepted."""
    for status in VALID_EPISTEMIC_STATUSES:
        ps = PerceivedSpace(space=Space(id="s1"), epistemic_status=status)
        assert ps.epistemic_status == status


def test_perception_to_dict_roundtrip():
    """Perception serializes to dict and reconstructs without structural loss."""
    p = Perception(
        id="perc-rt",
        actor_id="actor-rt",
        source_id="world-rt",
        schema_version="1.0",
    )
    p.perceived_spaces["s1"] = PerceivedSpace(
        space=Space(id="s1"),
        epistemic_status="believed",
        noise_metadata={"snr": 0.9},
    )
    p.perceived_memberships.append(
        PerceivedMembership(
            membership=SpaceObjectMembership(
                object_id="actor-x", space_id="s1", role="occupies"
            ),
            epistemic_status="certain",
        )
    )
    p.perceived_relations.append(
        PerceivedRelation(
            relation=SpaceRelation(
                source_space_id="s1",
                target_space_id="s2",
                relation_type="adjacent_to",
            ),
            epistemic_status="hypothesis",
        )
    )

    d = p.to_dict()
    restored = Perception.from_dict(d)

    assert restored.id == "perc-rt"
    assert restored.actor_id == "actor-rt"
    assert restored.source_id == "world-rt"
    assert "s1" in restored.perceived_spaces
    assert restored.perceived_spaces["s1"].epistemic_status == "believed"
    assert restored.perceived_spaces["s1"].noise_metadata == {"snr": 0.9}
    assert len(restored.perceived_memberships) == 1
    assert restored.perceived_memberships[0].membership.object_id == "actor-x"
    assert len(restored.perceived_relations) == 1
    assert restored.perceived_relations[0].epistemic_status == "hypothesis"


def test_perception_to_dict_contains_object_type():
    """to_dict always emits object_type = 'perception' (F-3)."""
    p = Perception(id="p1", actor_id="a1", source_id="w1")
    assert p.to_dict()["object_type"] == "perception"


def test_perception_query_memberships_for_object():
    """memberships_for_object filters by object_id."""
    p = Perception(id="p1", actor_id="a1", source_id="w1")
    p.perceived_memberships += [
        PerceivedMembership(
            membership=SpaceObjectMembership("actor-x", "s1", "occupies")
        ),
        PerceivedMembership(
            membership=SpaceObjectMembership("actor-y", "s1", "occupies")
        ),
        PerceivedMembership(
            membership=SpaceObjectMembership("actor-x", "s2", "observes")
        ),
    ]

    result = p.memberships_for_object("actor-x")
    assert len(result) == 2
    assert all(pm.membership.object_id == "actor-x" for pm in result)


def test_perception_query_memberships_in_space():
    """memberships_in_space filters by space_id."""
    p = Perception(id="p1", actor_id="a1", source_id="w1")
    p.perceived_memberships += [
        PerceivedMembership(
            membership=SpaceObjectMembership("actor-x", "s1", "occupies")
        ),
        PerceivedMembership(
            membership=SpaceObjectMembership("actor-y", "s2", "occupies")
        ),
    ]

    result = p.memberships_in_space("s1")
    assert len(result) == 1
    assert result[0].membership.space_id == "s1"


def test_perception_query_relations_for_space():
    """relations_for_space returns relations where the space is source or target."""
    p = Perception(id="p1", actor_id="a1", source_id="w1")
    p.perceived_relations += [
        PerceivedRelation(relation=SpaceRelation("s1", "s2", "adjacent_to")),
        PerceivedRelation(relation=SpaceRelation("s3", "s1", "adjacent_to")),
        PerceivedRelation(relation=SpaceRelation("s2", "s3", "adjacent_to")),
    ]

    result = p.relations_for_space("s1")
    assert len(result) == 2


# ============================================================
# Sensor tests
# ============================================================


def _build_world(world_id: str = "w") -> World:
    """Helper: build a small world with two spaces, one membership, one relation."""
    world = World(id=world_id)
    world.add_space(Space(id="s1"))
    world.add_space(Space(id="s2"))
    world.place_object("actor-1", "s1")
    world.add_space_relation(
        SpaceRelation(
            source_space_id="s1", target_space_id="s2", relation_type="adjacent_to"
        )
    )
    return world


def test_sensor_default_senses_all_elements():
    """Default sensor (TotalCoverage + IdentityNoise) copies all world elements."""
    world = _build_world("w-sens-1")
    sensor = Sensor()
    perception = sensor.sense(world, "actor-1")

    assert "s1" in perception.perceived_spaces
    assert "s2" in perception.perceived_spaces
    assert len(perception.perceived_memberships) == 1
    assert len(perception.perceived_relations) == 1


def test_sensor_invalid_epistemic_status_raises():
    """Sensor rejects an invalid default_epistemic_status."""
    with pytest.raises(ValueError):
        Sensor(default_epistemic_status="omniscient")


def test_sensor_custom_epistemic_status():
    """Sensor propagates its default_epistemic_status to every perceived element."""
    world = _build_world("w-epi-1")
    sensor = Sensor(default_epistemic_status="believed")
    perception = sensor.sense(world, "actor-1")

    for ps in perception.perceived_spaces.values():
        assert ps.epistemic_status == "believed"
    for pm in perception.perceived_memberships:
        assert pm.epistemic_status == "believed"
    for pr in perception.perceived_relations:
        assert pr.epistemic_status == "believed"


def test_sensor_coverage_rule_excludes_space():
    """A CoverageRule can make specific spaces invisible."""

    class HideS2(CoverageRule):
        def covers_space(self, space, actor_id, world):
            return space.id != "s2"

        def covers_membership(self, membership, actor_id, world):
            return membership.space_id != "s2"

        def covers_relation(self, relation, actor_id, world):
            return True

    world = _build_world("w-cov-1")
    sensor = Sensor(coverage_rules=[HideS2()])
    perception = sensor.sense(world, "actor-1")

    assert "s1" in perception.perceived_spaces
    assert "s2" not in perception.perceived_spaces


def test_sensor_coverage_rule_excludes_membership():
    """A CoverageRule can hide memberships from perception."""

    class HideAllMemberships(CoverageRule):
        def covers_space(self, space, actor_id, world):
            return True

        def covers_membership(self, membership, actor_id, world):
            return False

        def covers_relation(self, relation, actor_id, world):
            return True

    world = _build_world("w-cov-2")
    sensor = Sensor(coverage_rules=[HideAllMemberships()])
    perception = sensor.sense(world, "actor-1")

    assert len(perception.perceived_memberships) == 0


def test_sensor_coverage_rule_excludes_relation():
    """A CoverageRule can hide space relations from perception."""

    class HideAllRelations(CoverageRule):
        def covers_space(self, space, actor_id, world):
            return True

        def covers_membership(self, membership, actor_id, world):
            return True

        def covers_relation(self, relation, actor_id, world):
            return False

    world = _build_world("w-cov-3")
    sensor = Sensor(coverage_rules=[HideAllRelations()])
    perception = sensor.sense(world, "actor-1")

    assert len(perception.perceived_relations) == 0


def test_sensor_noise_rule_modifies_space_attribute():
    """A NoiseRule can distort space attributes in the perception."""

    class LabelNoise(NoiseRule):
        def apply_to_space(self, space, actor_id):
            space.attributes["label"] = "noisy_label"
            return space, {"noise_type": "label_override"}

        def apply_to_membership(self, membership, actor_id):
            return membership, {}

        def apply_to_relation(self, relation, actor_id):
            return relation, {}

    world = _build_world("w-noise-1")
    sensor = Sensor(noise_rules=[LabelNoise()])
    perception = sensor.sense(world, "actor-1")

    ps = perception.get_perceived_space("s1")
    assert ps is not None
    assert ps.space.attributes.get("label") == "noisy_label"
    assert ps.noise_metadata == {"noise_type": "label_override"}


def test_sensor_noise_does_not_mutate_world():
    """Noise applied to a perception copy never modifies the original world space."""

    class CorruptingNoise(NoiseRule):
        def apply_to_space(self, space, actor_id):
            space.attributes["corrupted"] = True
            return space, {}

        def apply_to_membership(self, membership, actor_id):
            return membership, {}

        def apply_to_relation(self, relation, actor_id):
            return relation, {}

    world = _build_world("w-noise-2")
    sensor = Sensor(noise_rules=[CorruptingNoise()])
    sensor.sense(world, "actor-1")

    original = world.get_space("s1")
    assert original is not None
    assert "corrupted" not in original.attributes


def test_sensor_two_coverage_rules_and_logic():
    """Multiple coverage rules are combined with AND logic."""

    class AllowOnlyS1(CoverageRule):
        def covers_space(self, space, actor_id, world):
            return space.id == "s1"

        def covers_membership(self, membership, actor_id, world):
            return membership.space_id == "s1"

        def covers_relation(self, relation, actor_id, world):
            return True

    class AllowOnlyS2(CoverageRule):
        def covers_space(self, space, actor_id, world):
            return space.id == "s2"

        def covers_membership(self, membership, actor_id, world):
            return True

        def covers_relation(self, relation, actor_id, world):
            return True

    world = _build_world("w-and-1")
    sensor = Sensor(coverage_rules=[AllowOnlyS1(), AllowOnlyS2()])
    perception = sensor.sense(world, "actor-1")

    # Neither s1 (excluded by AllowOnlyS2) nor s2 (excluded by AllowOnlyS1)
    assert len(perception.perceived_spaces) == 0


def test_sensor_chained_noise_rules():
    """Multiple noise rules are applied sequentially; metadata is merged."""

    class AddFoo(NoiseRule):
        def apply_to_space(self, space, actor_id):
            return space, {"foo": 1}

        def apply_to_membership(self, membership, actor_id):
            return membership, {}

        def apply_to_relation(self, relation, actor_id):
            return relation, {}

    class AddBar(NoiseRule):
        def apply_to_space(self, space, actor_id):
            return space, {"bar": 2}

        def apply_to_membership(self, membership, actor_id):
            return membership, {}

        def apply_to_relation(self, relation, actor_id):
            return relation, {}

    world = _build_world("w-chain-1")
    sensor = Sensor(noise_rules=[AddFoo(), AddBar()])
    perception = sensor.sense(world, "actor-1")

    ps = perception.get_perceived_space("s1")
    assert ps is not None
    assert ps.noise_metadata == {"foo": 1, "bar": 2}


def test_sensor_multi_space_actor_perception():
    """An actor present in multiple spaces is fully perceived (A-3, P-3)."""
    world = World(id="w-multi")
    world.add_space(Space(id="phys"))
    world.add_space(Space(id="info"))
    world.place_object("actor-multi", "phys")
    world.place_object("actor-multi", "info")

    sensor = Sensor()
    perception = sensor.sense(world, "actor-multi")

    memberships = perception.memberships_for_object("actor-multi")
    space_ids = {pm.membership.space_id for pm in memberships}
    assert "phys" in space_ids
    assert "info" in space_ids


def test_sensor_perception_id_is_deterministic():
    """Same (actor_id, world.id, timestamp) always produces the same perception ID."""
    world = _build_world("w-id-1")
    sensor = Sensor()

    p1 = sensor.sense(world, "actor-1", timestamp=42)
    p2 = sensor.sense(world, "actor-1", timestamp=42)

    assert p1.id == p2.id


def test_sensor_perception_id_is_unique_without_timestamp():
    """Without a timestamp, each call produces a unique perception ID."""
    world = _build_world("w-id-2")
    sensor = Sensor()

    p1 = sensor.sense(world, "actor-1")
    p2 = sensor.sense(world, "actor-1")

    assert p1.id != p2.id


def test_sensor_identity_noise_rule_no_metadata():
    """IdentityNoiseRule always produces empty noise_metadata."""
    world = _build_world("w-idn-1")
    sensor = Sensor(noise_rules=[IdentityNoiseRule()])
    perception = sensor.sense(world, "actor-1")

    for ps in perception.perceived_spaces.values():
        assert ps.noise_metadata == {}
    for pm in perception.perceived_memberships:
        assert pm.noise_metadata == {}
    for pr in perception.perceived_relations:
        assert pr.noise_metadata == {}


# ============================================================
# Action tests
# ============================================================


def test_action_instantiation():
    """Verify that an action instantiates with required and default fields."""
    action = Action(
        id="action-1",
        actor_id="actor-1",
        world_id="world-1",
        space_id="space-1",
        action_type="move",
    )

    assert action.id == "action-1"
    assert action.actor_id == "actor-1"
    assert action.world_id == "world-1"
    assert action.space_id == "space-1"
    assert action.action_type == "move"
    assert action.schema_version == "1.0"
    assert action.resource_effects == []
    assert action.prerequisites == []
    assert action.outcome_description == ""
    assert isinstance(action.state_changes, dict)
    assert isinstance(action.context, dict)
    assert isinstance(action.provenance, dict)


def test_action_add_resource_effect():
    """Verify that resource effects can be added to an action."""
    action = Action(
        id="action-consume",
        actor_id="actor-1",
        world_id="world-1",
        space_id="space-1",
        action_type="consume",
    )

    effect = ResourceEffect(
        resource_id="energy-1",
        effect_type="consume",
        quantity=10.0,
        source_id="space-1",
        target_id="actor-1",
    )
    action.add_resource_effect(effect)

    assert len(action.resource_effects) == 1
    assert action.resource_effects[0].resource_id == "energy-1"
    assert action.resource_effects[0].quantity == 10.0


def test_action_add_prerequisite():
    """Verify that prerequisites can be added to an action."""
    action = Action(
        id="action-require-energy",
        actor_id="actor-1",
        world_id="world-1",
        space_id="space-1",
        action_type="attack",
    )

    prereq = ActionPrerequisite(
        prerequisite_type="resource",
        field_name="energy",
        required_value=5.0,
    )
    action.add_prerequisite(prereq)

    assert len(action.prerequisites) == 1
    assert action.prerequisites[0].field_name == "energy"
    assert action.prerequisites[0].required_value == 5.0


def test_action_set_state_change():
    """Verify that state changes can be set on an action."""
    action = Action(
        id="action-transform",
        actor_id="actor-1",
        world_id="world-1",
        space_id="space-1",
        action_type="transform",
    )

    action.set_state_change("space_temperature", 50.0)
    action.set_state_change("actor_energy", -10)

    assert action.state_changes["space_temperature"] == 50.0
    assert action.state_changes["actor_energy"] == -10


def test_action_to_dict_contains_required_fields():
    """Verify that action serialization includes all required fields."""
    action = Action(
        id="action-full",
        actor_id="actor-1",
        world_id="world-1",
        space_id="space-1",
        action_type="interact",
        outcome_description="Actor interacts with space",
    )
    action.add_resource_effect(
        ResourceEffect(
            resource_id="res-1",
            effect_type="produce",
            quantity=5.0,
        )
    )

    action_dict = action.to_dict()

    assert action_dict["id"] == "action-full"
    assert action_dict["object_type"] == "action"
    assert action_dict["schema_version"] == "1.0"
    assert isinstance(action_dict["attributes"], dict)
    assert isinstance(action_dict["relations"], dict)
    assert action_dict["actor_id"] == "actor-1"
    assert action_dict["world_id"] == "world-1"
    assert action_dict["space_id"] == "space-1"
    assert action_dict["action_type"] == "interact"
    assert action_dict["outcome_description"] == "Actor interacts with space"
    assert len(action_dict["resource_effects"]) == 1
    assert action_dict["resource_effects"][0]["resource_id"] == "res-1"


def test_action_to_dict_roundtrip():
    """Verify that an action can be serialized and deserialized without loss."""
    original = Action(
        id="action-rt",
        actor_id="actor-2",
        world_id="world-2",
        space_id="space-2",
        action_type="exchange",
        outcome_description="Exchange resources",
    )
    original.add_resource_effect(
        ResourceEffect(
            resource_id="gold",
            effect_type="transfer",
            quantity=20.0,
            source_id="actor-2",
            target_id="space-2",
        )
    )
    original.add_prerequisite(
        ActionPrerequisite(
            prerequisite_type="capability",
            field_name="trading_skill",
            required_value="advanced",
        )
    )
    original.set_attribute("difficulty", "high")
    original.add_relation("targets", "resource-market")
    original.set_state("phase", "open")
    original.set_provenance("source", "unit-test")
    original.set_state_change("market_value", 100)

    # Serialize and deserialize
    action_dict = original.to_dict()
    restored = Action.from_dict(action_dict)

    assert restored.id == original.id
    assert restored.actor_id == original.actor_id
    assert restored.world_id == original.world_id
    assert restored.space_id == original.space_id
    assert restored.action_type == original.action_type
    assert restored.outcome_description == original.outcome_description
    assert len(restored.resource_effects) == len(original.resource_effects)
    assert (
        restored.resource_effects[0].resource_id
        == original.resource_effects[0].resource_id
    )
    assert len(restored.prerequisites) == len(original.prerequisites)
    assert restored.prerequisites[0].field_name == original.prerequisites[0].field_name
    assert restored.attributes == original.attributes
    assert restored.relations == original.relations
    assert restored.state == original.state
    assert restored.provenance == original.provenance
    assert restored.state_changes == original.state_changes


def test_action_missing_actor_id_raises():
    """Action must be bound to a performer actor."""
    with pytest.raises(ValueError):
        Action(
            id="action-missing-actor",
            actor_id="",
            world_id="world-1",
            space_id="space-1",
            action_type="move",
        )


def test_action_deterministic_serialization():
    """Verify that action serialization is deterministic (sorted fields)."""
    action = Action(
        id="action-det",
        actor_id="actor-1",
        world_id="world-1",
        space_id="space-1",
        action_type="test",
    )

    # Add effects in non-alphabetical order
    action.add_resource_effect(
        ResourceEffect(
            resource_id="z-res",
            effect_type="consume",
        )
    )
    action.add_resource_effect(
        ResourceEffect(
            resource_id="a-res",
            effect_type="produce",
        )
    )

    # Serialize twice
    dict1 = action.to_dict()
    dict2 = action.to_dict()

    # Both serializations must be identical (proves determinism)
    assert dict1 == dict2
    # Resources must be sorted by (resource_id, effect_type)
    assert dict1["resource_effects"][0]["resource_id"] == "a-res"
    assert dict1["resource_effects"][1]["resource_id"] == "z-res"


def test_action_deterministic_serialization_resource_effect_metadata_tie_break():
    """resource_effects ordering should remain deterministic when only metadata differs."""
    action = Action(
        id="action-det-meta-re",
        actor_id="actor-1",
        world_id="world-1",
        space_id="space-1",
        action_type="test",
    )
    # Same primary keys, different metadata; insertion order is reversed on purpose.
    action.add_resource_effect(
        ResourceEffect(
            resource_id="res",
            effect_type="consume",
            quantity=1.0,
            source_id="s",
            target_id="t",
            metadata={"z": 1},
        )
    )
    action.add_resource_effect(
        ResourceEffect(
            resource_id="res",
            effect_type="consume",
            quantity=1.0,
            source_id="s",
            target_id="t",
            metadata={"a": 1},
        )
    )

    d = action.to_dict()
    assert d["resource_effects"][0]["metadata"] == {"a": 1}
    assert d["resource_effects"][1]["metadata"] == {"z": 1}


def test_action_deterministic_serialization_prerequisite_metadata_tie_break():
    """prerequisites ordering should remain deterministic when only metadata differs."""
    action = Action(
        id="action-det-meta-pre",
        actor_id="actor-1",
        world_id="world-1",
        space_id="space-1",
        action_type="test",
    )
    # Same primary keys, different metadata; insertion order is reversed on purpose.
    action.add_prerequisite(
        ActionPrerequisite(
            prerequisite_type="resource",
            field_name="energy",
            required_value=5,
            metadata={"z": 1},
        )
    )
    action.add_prerequisite(
        ActionPrerequisite(
            prerequisite_type="resource",
            field_name="energy",
            required_value=5,
            metadata={"a": 1},
        )
    )

    d = action.to_dict()
    assert d["prerequisites"][0]["metadata"] == {"a": 1}
    assert d["prerequisites"][1]["metadata"] == {"z": 1}


def test_resource_effect_instantiation():
    """Verify that a resource effect instantiates correctly."""
    effect = ResourceEffect(
        resource_id="water",
        effect_type="consume",
        quantity=50.0,
        source_id="lake-1",
        target_id="actor-1",
    )

    assert effect.resource_id == "water"
    assert effect.effect_type == "consume"
    assert effect.quantity == 50.0
    assert effect.source_id == "lake-1"
    assert effect.target_id == "actor-1"


def test_resource_effect_to_dict_roundtrip():
    """Verify that a resource effect serializes and deserializes correctly."""
    original = ResourceEffect(
        resource_id="iron",
        effect_type="transfer",
        quantity=100.0,
        source_id="mine-1",
        target_id="factory-1",
        metadata={"quality": "high", "purity": 95},
    )

    effect_dict = original.to_dict()
    restored = ResourceEffect.from_dict(effect_dict)

    assert restored.resource_id == original.resource_id
    assert restored.effect_type == original.effect_type
    assert restored.quantity == original.quantity
    assert restored.source_id == original.source_id
    assert restored.target_id == original.target_id
    assert restored.metadata == original.metadata


def test_action_prerequisite_instantiation():
    """Verify that an action prerequisite instantiates correctly."""
    prereq = ActionPrerequisite(
        prerequisite_type="perception",
        field_name="enemy_sighted",
        required_value=True,
        metadata={"confidence": 0.8},
    )

    assert prereq.prerequisite_type == "perception"
    assert prereq.field_name == "enemy_sighted"
    assert prereq.required_value is True
    assert prereq.metadata["confidence"] == 0.8


def test_action_prerequisite_to_dict_roundtrip():
    """Verify that a prerequisite serializes and deserializes correctly."""
    original = ActionPrerequisite(
        prerequisite_type="space_rule",
        field_name="gravity_enabled",
        required_value=False,
        metadata={"reason": "zero-g space"},
    )

    prereq_dict = original.to_dict()
    restored = ActionPrerequisite.from_dict(prereq_dict)

    assert restored.prerequisite_type == original.prerequisite_type
    assert restored.field_name == original.field_name
    assert restored.required_value == original.required_value
    assert restored.metadata == original.metadata


# ============================================================
# Null-handling deserialization tests
# ============================================================


def test_model_object_from_dict_null_optional_maps_defaults_empty():
    """ModelObject.from_dict should treat null optional maps as empty dicts."""
    obj = ModelObject.from_dict(
        {
            "id": "obj-null-1",
            "object_type": "generic",
            "attributes": None,
            "relations": None,
            "state": None,
            "context": None,
            "provenance": None,
        }
    )
    assert obj.attributes == {}
    assert obj.relations == {}
    assert obj.state == {}
    assert obj.context == {}
    assert obj.provenance == {}


def test_model_object_from_dict_null_required_raises():
    """ModelObject.from_dict should reject null required identity fields."""
    with pytest.raises(ValueError):
        ModelObject.from_dict({"id": None, "object_type": "generic"})
    with pytest.raises(ValueError):
        ModelObject.from_dict({"id": "obj-1", "object_type": None})


def test_actor_resource_space_from_dict_null_optional_maps_defaults_empty():
    """Actor/Resource/Space should accept null optional maps in from_dict."""
    actor = Actor.from_dict({"id": "a-null", "attributes": None, "relations": None})
    resource = Resource.from_dict(
        {"id": "r-null", "attributes": None, "relations": None}
    )
    space = Space.from_dict({"id": "s-null", "attributes": None, "relations": None})

    assert isinstance(actor.attributes, dict)
    assert actor.relations == {}
    assert isinstance(resource.attributes, dict)
    assert resource.relations == {}
    assert isinstance(space.attributes, dict)
    assert space.relations == {}


def test_graph_from_dict_null_collections_defaults_empty():
    """Graph deserializers should treat null collections as empty."""
    sog = SpaceObjectGraph.from_dict({"spaces": None, "object_memberships": None})
    srg = SpaceRelationGraph.from_dict({"relations": None})
    assert sog.spaces == {}
    assert sog.object_memberships == []
    assert srg.relations == []


def test_membership_and_relation_from_dict_null_required_raises():
    """Membership and relation deserializers should reject null required IDs."""
    with pytest.raises(ValueError):
        SpaceObjectMembership.from_dict(
            {"object_id": None, "space_id": "s1", "role": "occupies"}
        )
    with pytest.raises(ValueError):
        SpaceRelation.from_dict(
            {
                "source_space_id": None,
                "target_space_id": "s2",
                "relation_type": "adjacent_to",
            }
        )


def test_perception_from_dict_null_optional_collections_defaults_empty():
    """Perception.from_dict should normalize null optional collections to empty."""
    p = Perception.from_dict(
        {
            "id": "p-null-1",
            "actor_id": "a1",
            "source_id": "w1",
            "perceived_spaces": None,
            "perceived_memberships": None,
            "perceived_relations": None,
            "context": None,
            "provenance": None,
            "timestamp": None,
        }
    )
    assert p.perceived_spaces == {}
    assert p.perceived_memberships == []
    assert p.perceived_relations == []
    assert p.context == {}
    assert p.provenance == {}


def test_perceived_wrappers_from_dict_null_noise_defaults_empty():
    """Perceived* wrappers should treat null noise metadata as empty dict."""
    ps = PerceivedSpace.from_dict(
        {
            "space": Space(id="s1").to_dict(),
            "epistemic_status": "certain",
            "noise_metadata": None,
        }
    )
    pm = PerceivedMembership.from_dict(
        {
            "membership": SpaceObjectMembership("a1", "s1", "occupies").to_dict(),
            "epistemic_status": "certain",
            "noise_metadata": None,
        }
    )
    pr = PerceivedRelation.from_dict(
        {
            "relation": SpaceRelation("s1", "s2", "adjacent_to").to_dict(),
            "epistemic_status": "certain",
            "noise_metadata": None,
        }
    )
    assert ps.noise_metadata == {}
    assert pm.noise_metadata == {}
    assert pr.noise_metadata == {}


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


def test_action_related_from_dict_null_handling():
    """Action-related from_dict methods should default null optional payloads."""
    action = Action.from_dict(
        {
            "id": "act-null",
            "object_type": "action",
            "actor_id": "a1",
            "world_id": "w1",
            "space_id": "s1",
            "action_type": None,
            "resource_effects": None,
            "prerequisites": None,
            "outcome_description": None,
            "state_changes": None,
            "attributes": None,
            "relations": None,
            "state": None,
            "context": None,
            "provenance": None,
        }
    )
    assert action.action_type == "generic"
    assert action.resource_effects == []
    assert action.prerequisites == []
    assert action.outcome_description == ""
    assert action.state_changes == {}
    assert action.attributes == {}
    assert action.relations == {}

    effect = ResourceEffect.from_dict(
        {
            "resource_id": "res1",
            "effect_type": None,
            "quantity": None,
            "metadata": None,
        }
    )
    prereq = ActionPrerequisite.from_dict(
        {"field_name": "energy", "prerequisite_type": None, "metadata": None}
    )
    assert effect.effect_type == "consume"
    assert effect.quantity == 1.0
    assert effect.metadata == {}
    assert prereq.prerequisite_type == "resource"
    assert prereq.metadata == {}


def test_action_related_from_dict_null_required_raises():
    """Action-related from_dict should reject null required fields."""
    with pytest.raises(ValueError):
        Action.from_dict(
            {
                "id": "act-bad",
                "object_type": "action",
                "actor_id": None,
                "world_id": "w1",
                "space_id": "s1",
            }
        )
    with pytest.raises(ValueError):
        ResourceEffect.from_dict({"resource_id": None})
    with pytest.raises(ValueError):
        ActionPrerequisite.from_dict({"field_name": None})
