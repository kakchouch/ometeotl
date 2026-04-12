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
    """The same (actor_id, world.id) always produces the same perception ID."""
    world = _build_world("w-id-1")
    sensor = Sensor()

    p1 = sensor.sense(world, "actor-1")
    p2 = sensor.sense(world, "actor-1")

    assert p1.id == p2.id


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
