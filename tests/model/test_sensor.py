"""Tests for masm.model.sensor."""

import pytest

from masm.model.sensor import CoverageRule, IdentityNoiseRule, NoiseRule, Sensor
from masm.model.space_relations import SpaceRelation
from masm.model.spaces import Space
from masm.model.world import World


def _build_world(world_id: str = "w") -> World:
    """Build a small world with two spaces, one membership, and one relation."""
    world = World(id=world_id)
    world.add_space(Space(id="s1"))
    world.add_space(Space(id="s2"))
    world.place_object("actor-1", "s1")
    world.add_space_relation(
        SpaceRelation(
            source_space_id="s1",
            target_space_id="s2",
            relation_type="adjacent_to",
        )
    )
    return world


def test_sensor_default_senses_all_elements():
    """Default sensor copies all world elements."""
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

    for perceived_space in perception.perceived_spaces.values():
        assert perceived_space.epistemic_status == "believed"
    for perceived_membership in perception.perceived_memberships:
        assert perceived_membership.epistemic_status == "believed"
    for perceived_relation in perception.perceived_relations:
        assert perceived_relation.epistemic_status == "believed"


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

    perceived_space = perception.get_perceived_space("s1")
    assert perceived_space is not None
    assert perceived_space.space.attributes.get("label") == "noisy_label"
    assert perceived_space.noise_metadata == {"noise_type": "label_override"}


def test_sensor_noise_does_not_mutate_world():
    """Noise applied to a perception copy never modifies the original world."""

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

    perceived_space = perception.get_perceived_space("s1")
    assert perceived_space is not None
    assert perceived_space.noise_metadata == {"foo": 1, "bar": 2}


def test_sensor_multi_space_actor_perception():
    """An actor present in multiple spaces is fully perceived."""
    world = World(id="w-multi")
    world.add_space(Space(id="phys"))
    world.add_space(Space(id="info"))
    world.place_object("actor-multi", "phys")
    world.place_object("actor-multi", "info")

    sensor = Sensor()
    perception = sensor.sense(world, "actor-multi")

    memberships = perception.memberships_for_object("actor-multi")
    space_ids = {item.membership.space_id for item in memberships}
    assert "phys" in space_ids
    assert "info" in space_ids


def test_sensor_perception_id_is_deterministic():
    """Same (actor_id, world.id, timestamp) always produces the same perception ID."""
    world = _build_world("w-id-1")
    sensor = Sensor()

    first = sensor.sense(world, "actor-1", timestamp=42)
    second = sensor.sense(world, "actor-1", timestamp=42)

    assert first.id == second.id


def test_sensor_perception_id_is_unique_without_timestamp():
    """Without a timestamp, each call produces a unique perception ID."""
    world = _build_world("w-id-2")
    sensor = Sensor()

    first = sensor.sense(world, "actor-1")
    second = sensor.sense(world, "actor-1")

    assert first.id != second.id


def test_sensor_identity_noise_rule_no_metadata():
    """IdentityNoiseRule always produces empty noise_metadata."""
    world = _build_world("w-idn-1")
    sensor = Sensor(noise_rules=[IdentityNoiseRule()])
    perception = sensor.sense(world, "actor-1")

    for perceived_space in perception.perceived_spaces.values():
        assert perceived_space.noise_metadata == {}
    for perceived_membership in perception.perceived_memberships:
        assert perceived_membership.noise_metadata == {}
    for perceived_relation in perception.perceived_relations:
        assert perceived_relation.noise_metadata == {}
