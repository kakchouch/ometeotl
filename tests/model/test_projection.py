"""Tests for masm.model.projection."""

import pytest

from masm.model.actions import Action, ActionPrerequisite, ResourceEffect
from masm.model.perception import Perception
from masm.model.projection import (
    ActionProjection,
    DefaultProjectionTool,
    ProjectedPerceptionChange,
    ProjectedPerceptionState,
    ProjectionAssumption,
    ProjectionBatch,
    project_actions,
)
from masm.model.resources import Resource
from masm.model.sensor import Sensor
from masm.model.spaces import Space
from masm.model.world import World


def _build_projection_action() -> Action:
    return Action(
        id="action-proj-1",
        actor_id="actor-1",
        world_id="world-1",
        space_id="space-1",
        action_type="consume",
        resource_effects=[
            ResourceEffect(
                resource_id="energy-1",
                effect_type="consume",
                quantity=2.0,
                source_id="actor-1",
            )
        ],
        prerequisites=[
            ActionPrerequisite(
                prerequisite_type="capability",
                field_name="can_consume",
                required_value=True,
            )
        ],
    )


def test_projection_builds_assumptions_from_action_perception_and_resources():
    """Projection produces assumption sets without building strategy nodes."""
    action = _build_projection_action()
    perception = Perception(
        id="perception-proj-1",
        actor_id="actor-1",
        source_id="world-1",
    )
    resource = Resource(id="energy-1")

    projection = DefaultProjectionTool().project_action(
        action,
        perception,
        resources=[resource],
    )

    assumption_ids = {assumption.assumption_id for assumption in projection.assumptions}

    assert projection.status == "projected"
    assert projection.metadata["projection_basis"] == "perception"
    assert projection.resource_ids == ["energy-1"]
    assert projection.projected_state is not None
    assert projection.projected_state.source_perception_id == perception.id
    assert projection.projected_state.generating_action_id == action.id
    assert f"{action.id}:actor_binding" in assumption_ids
    assert f"{action.id}:source_context" in assumption_ids
    assert f"{action.id}:effect:energy-1:consume" in assumption_ids
    assert f"{action.id}:prerequisite:capability:can_consume" in assumption_ids


def test_projection_blocks_on_actor_mismatch():
    """Projection rejects actions evaluated through another actor's perception."""
    action = _build_projection_action()
    perception = Perception(
        id="perception-proj-2",
        actor_id="actor-2",
        source_id="world-1",
    )

    projection = DefaultProjectionTool().project_action(action, perception)

    assert projection.status == "blocked"
    actor_assumption = next(
        assumption
        for assumption in projection.assumptions
        if assumption.assumption_type == "actor_binding"
    )
    assert actor_assumption.satisfied is False


def test_projection_marks_missing_required_resources_partial():
    """Missing required consume/transfer resources are surfaced as partial projections."""
    action = _build_projection_action()
    perception = Perception(
        id="perception-proj-3",
        actor_id="actor-1",
        source_id="world-1",
    )

    projection = DefaultProjectionTool().project_action(action, perception)

    assert projection.status == "partial"
    resource_assumption = next(
        assumption
        for assumption in projection.assumptions
        if assumption.assumption_type == "resource_effect"
    )
    assert resource_assumption.satisfied is False


def test_projection_batch_round_trip_serialization():
    """Projection batches stay deterministic under serialization round-trips."""
    action = _build_projection_action()
    perception = Perception(
        id="perception-proj-4",
        actor_id="actor-1",
        source_id="world-1",
    )
    batch = project_actions([action], perception, resources=[Resource(id="energy-1")])

    payload = batch.to_dict()
    restored = ProjectionBatch.from_dict(payload)

    assert restored.to_dict() == payload
    assert (
        ActionProjection.from_dict(payload["projections"][0]).to_dict()
        == payload["projections"][0]
    )


def test_projection_builds_successor_perceived_state_from_previous_perception():
    """Projected perceptions carry forward and mutate the prior perceived state."""
    world = World(id="world-proj-state-1")
    world.add_space(Space(id="space-1"))
    world.place_object("energy-1", "space-1")
    perception = Sensor().sense(world, "actor-1")

    action = _build_projection_action()
    action.state_changes = {"context_updates": {"next_focus": "regroup"}}

    projection = DefaultProjectionTool().project_action(
        action,
        perception,
        resources=[Resource(id="energy-1")],
    )

    assert projection.projected_state is not None
    successor = projection.projected_state.perception

    assert successor.id == f"projection-{perception.id}-{action.id}"
    assert successor.context["next_focus"] == "regroup"
    assert successor.memberships_for_object("energy-1") == []
    assert all(
        perceived_space.epistemic_status == "projected"
        for perceived_space in successor.perceived_spaces.values()
    )


def test_projected_perception_state_round_trip_serialization():
    """Projected successor states remain deterministic under serialization."""
    state = ProjectedPerceptionState(
        source_perception_id="perception-1",
        generating_action_id="action-1",
        perception=Perception(id="projection-1", actor_id="actor-1", source_id="w-1"),
        changes=[
            ProjectedPerceptionChange(
                change_id="action-1:state_changes",
                change_type="state_changes",
                subject_id="action-1",
                applied=True,
                metadata={"state_changes": {"context_updates": {"a": 1}}},
            )
        ],
        metadata={"projection_basis": "perception"},
    )

    payload = state.to_dict()
    restored = ProjectedPerceptionState.from_dict(payload)

    assert restored.to_dict() == payload


def test_projection_assumption_from_dict_rejects_non_boolean_satisfied():
    """Projection assumptions should reject non-boolean satisfied payloads."""
    with pytest.raises(TypeError, match="ProjectionAssumption.satisfied"):
        ProjectionAssumption.from_dict(
            {
                "assumption_id": "assumption-1",
                "assumption_type": "actor_binding",
                "description": "Actor binding must remain explicit.",
                "satisfied": "false",
            }
        )
