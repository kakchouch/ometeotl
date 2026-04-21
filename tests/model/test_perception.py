"""Tests for masm.model.perception."""

import pytest

from masm.model.perception import (
    VALID_EPISTEMIC_STATUSES,
    PerceivedMembership,
    PerceivedRelation,
    PerceivedSpace,
    Perception,
)
from masm.model.space_relations import SpaceRelation
from masm.model.spaces import Space, SpaceObjectMembership


def test_perception_instantiation():
    """Perception instantiates with correct defaults."""
    perception = Perception(id="perc-1", actor_id="actor-1", source_id="world-1")

    assert perception.id == "perc-1"
    assert perception.actor_id == "actor-1"
    assert perception.source_id == "world-1"
    assert perception.schema_version == "1.0"
    assert perception.perceived_spaces == {}
    assert perception.perceived_memberships == []
    assert perception.perceived_relations == []


def test_perceived_space_invalid_epistemic_status_raises():
    """PerceivedSpace rejects an unknown epistemic status."""
    with pytest.raises(ValueError):
        PerceivedSpace(space=Space(id="s1"), epistemic_status="omniscient")


def test_perceived_membership_invalid_epistemic_status_raises():
    """PerceivedMembership rejects an unknown epistemic status."""
    with pytest.raises(ValueError):
        PerceivedMembership(
            membership=SpaceObjectMembership(
                object_id="a",
                space_id="s",
                role="occupies",
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
        perceived_space = PerceivedSpace(space=Space(id="s1"), epistemic_status=status)
        assert perceived_space.epistemic_status == status


def test_perception_to_dict_roundtrip():
    """Perception serializes to dict and reconstructs without structural loss."""
    perception = Perception(
        id="perc-rt",
        actor_id="actor-rt",
        source_id="world-rt",
        schema_version="1.0",
    )
    perception.perceived_spaces["s1"] = PerceivedSpace(
        space=Space(id="s1"),
        epistemic_status="believed",
        noise_metadata={"snr": 0.9},
    )
    perception.perceived_memberships.append(
        PerceivedMembership(
            membership=SpaceObjectMembership(
                object_id="actor-x",
                space_id="s1",
                role="occupies",
            ),
            epistemic_status="certain",
        )
    )
    perception.perceived_relations.append(
        PerceivedRelation(
            relation=SpaceRelation(
                source_space_id="s1",
                target_space_id="s2",
                relation_type="adjacent_to",
            ),
            epistemic_status="hypothesis",
        )
    )

    restored = Perception.from_dict(perception.to_dict())

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
    """to_dict always emits object_type = 'perception'."""
    perception = Perception(id="p1", actor_id="a1", source_id="w1")
    assert perception.to_dict()["object_type"] == "perception"


def test_perception_query_memberships_for_object():
    """memberships_for_object filters by object_id."""
    perception = Perception(id="p1", actor_id="a1", source_id="w1")
    perception.perceived_memberships += [
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

    result = perception.memberships_for_object("actor-x")
    assert len(result) == 2
    assert all(item.membership.object_id == "actor-x" for item in result)


def test_perception_query_memberships_in_space():
    """memberships_in_space filters by space_id."""
    perception = Perception(id="p1", actor_id="a1", source_id="w1")
    perception.perceived_memberships += [
        PerceivedMembership(
            membership=SpaceObjectMembership("actor-x", "s1", "occupies")
        ),
        PerceivedMembership(
            membership=SpaceObjectMembership("actor-y", "s2", "occupies")
        ),
    ]

    result = perception.memberships_in_space("s1")
    assert len(result) == 1
    assert result[0].membership.space_id == "s1"


def test_perception_query_relations_for_space():
    """relations_for_space returns relations where the space is source or target."""
    perception = Perception(id="p1", actor_id="a1", source_id="w1")
    perception.perceived_relations += [
        PerceivedRelation(relation=SpaceRelation("s1", "s2", "adjacent_to")),
        PerceivedRelation(relation=SpaceRelation("s3", "s1", "adjacent_to")),
        PerceivedRelation(relation=SpaceRelation("s2", "s3", "adjacent_to")),
    ]

    result = perception.relations_for_space("s1")
    assert len(result) == 2


def test_perception_from_dict_null_optional_collections_defaults_empty():
    """Perception.from_dict should normalize null optional collections to empty."""
    perception = Perception.from_dict(
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
    assert perception.perceived_spaces == {}
    assert perception.perceived_memberships == []
    assert perception.perceived_relations == []
    assert perception.context == {}
    assert perception.provenance == {}


def test_perceived_wrappers_from_dict_null_noise_defaults_empty():
    """Perceived* wrappers should treat null noise metadata as empty dict."""
    perceived_space = PerceivedSpace.from_dict(
        {
            "space": Space(id="s1").to_dict(),
            "epistemic_status": "certain",
            "noise_metadata": None,
        }
    )
    perceived_membership = PerceivedMembership.from_dict(
        {
            "membership": SpaceObjectMembership("a1", "s1", "occupies").to_dict(),
            "epistemic_status": "certain",
            "noise_metadata": None,
        }
    )
    perceived_relation = PerceivedRelation.from_dict(
        {
            "relation": SpaceRelation("s1", "s2", "adjacent_to").to_dict(),
            "epistemic_status": "certain",
            "noise_metadata": None,
        }
    )
    assert perceived_space.noise_metadata == {}
    assert perceived_membership.noise_metadata == {}
    assert perceived_relation.noise_metadata == {}


def test_perception_from_dict_rejects_unsupported_schema_version():
    """Perception payloads also enforce schema-version compatibility."""
    with pytest.raises(ValueError):
        Perception.from_dict(
            {
                "id": "p-schema-1",
                "actor_id": "a1",
                "source_id": "w1",
                "schema_version": "2.0",
            }
        )
