"""Tests for masm.validation.temporal."""

from masm.model.actions import Action
from masm.validation.base import ValidationContext
from masm.validation.temporal import TemporalValidator


def test_temporal_validator_rejects_outside_validity_window():
    """Interaction time outside actor validity should fail."""
    action = Action(
        id="a-1",
        actor_id="actor-1",
        world_id="world-1",
        space_id="space-1",
        action_type="move",
    )
    context = ValidationContext(
        metadata={
            "interaction_time": 20,
            "actor_validity": {
                "actor-1": {"start": 0, "end": 10}
            },
        }
    )

    result = TemporalValidator().validate(action, context)

    assert result.valid is False
    assert result.errors[0].code == "TEMP-OUTSIDE-VALIDITY"


def test_temporal_validator_skips_without_interaction_time():
    """Temporal validator should be silent when time context is missing."""
    action = Action(
        id="a-2",
        actor_id="actor-1",
        world_id="world-1",
        space_id="space-1",
        action_type="move",
    )

    result = TemporalValidator().validate(
        action, ValidationContext()
    )

    assert result.valid is True
    assert result.summary["total"] == 0


def test_temporal_validator_skips_without_actor_id():
    """Temporal validator should be silent for non actor-based payloads."""
    payload = {"id": "system-action", "space_id": "space-1"}
    context = ValidationContext(metadata={"interaction_time": 5})

    result = TemporalValidator().validate(payload, context)

    assert result.valid is True
    assert result.summary["total"] == 0


def test_temporal_validator_reports_normalization_failure_as_issue():
    """Invalid temporal formats should produce structured errors, not raises."""
    action = Action(
        id="a-3",
        actor_id="actor-1",
        world_id="world-1",
        space_id="space-1",
        action_type="move",
    )
    context = ValidationContext(
        metadata={
            "interaction_time": "not-a-time",
            "actor_validity": {
                "actor-1": {"start": 0, "end": 10}
            },
        }
    )

    result = TemporalValidator().validate(action, context)

    assert result.valid is False
    assert result.errors[0].code == "TEMP-NORMALIZATION-FAILED"
