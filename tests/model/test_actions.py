"""Tests for masm.model.actions."""

import pytest

from masm.model.actions import Action, ActionPrerequisite, ResourceEffect


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

    restored = Action.from_dict(original.to_dict())

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
    """Verify that action serialization is deterministic."""
    action = Action(
        id="action-det",
        actor_id="actor-1",
        world_id="world-1",
        space_id="space-1",
        action_type="test",
    )

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

    first = action.to_dict()
    second = action.to_dict()

    assert first == second
    assert first["resource_effects"][0]["resource_id"] == "a-res"
    assert first["resource_effects"][1]["resource_id"] == "z-res"


def test_action_deterministic_serialization_resource_effect_metadata_tie_break():
    """resource_effects ordering should remain deterministic when metadata differs."""
    action = Action(
        id="action-det-meta-re",
        actor_id="actor-1",
        world_id="world-1",
        space_id="space-1",
        action_type="test",
    )
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

    payload = action.to_dict()
    assert payload["resource_effects"][0]["metadata"] == {"a": 1}
    assert payload["resource_effects"][1]["metadata"] == {"z": 1}


def test_action_deterministic_serialization_prerequisite_metadata_tie_break():
    """prerequisites ordering should remain deterministic when metadata differs."""
    action = Action(
        id="action-det-meta-pre",
        actor_id="actor-1",
        world_id="world-1",
        space_id="space-1",
        action_type="test",
    )
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

    payload = action.to_dict()
    assert payload["prerequisites"][0]["metadata"] == {"a": 1}
    assert payload["prerequisites"][1]["metadata"] == {"z": 1}


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

    restored = ResourceEffect.from_dict(original.to_dict())

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

    restored = ActionPrerequisite.from_dict(original.to_dict())

    assert restored.prerequisite_type == original.prerequisite_type
    assert restored.field_name == original.field_name
    assert restored.required_value == original.required_value
    assert restored.metadata == original.metadata


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


def test_action_to_dict_rejects_non_json_serializable_metadata():
    """Action serialization must fail fast on non-canonical metadata types."""
    action = Action(
        id="action-non-json-meta",
        actor_id="actor-1",
        world_id="world-1",
        space_id="space-1",
        action_type="test",
    )
    action.add_resource_effect(
        ResourceEffect(
            resource_id="res-x",
            effect_type="consume",
            metadata={"bad": object()},
        )
    )

    with pytest.raises(ValueError):
        action.to_dict()
