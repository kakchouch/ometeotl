"""Tests for ometeotl_core.validation.admissibility."""

from ometeotl_core.model.actors import Actor
from ometeotl_core.model.goals import Goal
from ometeotl_core.model.perception import Perception
from ometeotl_core.validation.admissibility import AdmissibilityValidator
from ometeotl_core.validation.base import ValidationContext


def test_admissibility_validator_accepts_admissible_goal():
    """Goal linked to actor with matching perception should be admissible."""
    goal = Goal(
        id="goal-1",
        actor_id="actor-1",
        target_condition={"x": 1},
    )
    actor = Actor(id="actor-1")
    actor.add_goal(goal.id)
    perception = Perception(
        id="p-1", actor_id="actor-1", source_id="world-1"
    )

    result = AdmissibilityValidator().validate(
        {"goal": goal, "actor": actor, "perception": perception},
        ValidationContext(),
    )

    assert result.valid is True


def test_admissibility_validator_rejects_actor_mismatch():
    """Actor/goal mismatches should be rejected."""
    goal = Goal(
        id="goal-2",
        actor_id="actor-2",
        target_condition={"x": 1},
    )
    actor = Actor(id="actor-1")
    actor.add_goal(goal.id)
    perception = Perception(
        id="p-2", actor_id="actor-1", source_id="world-1"
    )

    result = AdmissibilityValidator().validate(
        {"goal": goal, "actor": actor, "perception": perception},
        ValidationContext(),
    )

    assert result.valid is False
    assert result.errors[0].code == "ADM-NOT-ADMISSIBLE"
