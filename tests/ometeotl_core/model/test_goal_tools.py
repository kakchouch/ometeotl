"""Tests for ometeotl_core.model.goal_tools."""

from __future__ import annotations

from ometeotl_core.model.actions import Action
from ometeotl_core.model.actors import Actor
from ometeotl_core.model.goal_tools import (
    DefaultGoalFeasibilityTool,
    GoalAdmissibilityChecker,
    GoalAdmissibilityResult,
    GoalFeasibilityResult,
)
from ometeotl_core.model.goals import Goal
from ometeotl_core.model.perception import Perception
from ometeotl_core.model.projection import DefaultProjectionTool


def _build_projected_state(*, actor_id: str = "actor-1"):
    action = Action(
        id="action-project-1",
        actor_id=actor_id,
        world_id="world-1",
        space_id="space-1",
        action_type="move",
        state_changes={"context_updates": {"phase": "secure", "score": 10}},
    )
    perception = Perception(
        id="perception-root",
        actor_id=actor_id,
        source_id="world-1",
    )
    projection = DefaultProjectionTool().project_action(action, perception)
    assert projection.projected_state is not None
    return projection.projected_state


def test_default_goal_feasibility_tool_reachable_when_all_keys_match():
    projected = _build_projected_state()
    goal = Goal(
        id="goal-1",
        actor_id="actor-1",
        target_condition={"phase": "secure", "score": 10},
    )

    result = DefaultGoalFeasibilityTool().evaluate(goal, projected)

    assert result.reachable is True
    assert result.confidence == 1.0
    assert result.matching_keys == ["phase", "score"]


def test_default_goal_feasibility_tool_partial_match_returns_fractional_confidence():
    projected = _build_projected_state()
    goal = Goal(
        id="goal-2",
        actor_id="actor-1",
        target_condition={"phase": "secure", "score": 99},
    )

    result = DefaultGoalFeasibilityTool().evaluate(goal, projected)

    assert result.reachable is False
    assert result.confidence == 0.5
    assert result.matching_keys == ["phase"]


def test_default_goal_feasibility_tool_non_reachable_when_no_key_matches():
    projected = _build_projected_state()
    goal = Goal(
        id="goal-3",
        actor_id="actor-1",
        target_condition={"phase": "observe", "score": -1},
    )

    result = DefaultGoalFeasibilityTool().evaluate(goal, projected)

    assert result.reachable is False
    assert result.confidence == 0.0
    assert result.matching_keys == []


def test_default_goal_feasibility_tool_rejects_target_perception_mismatch():
    projected = _build_projected_state()
    goal = Goal(
        id="goal-4",
        actor_id="actor-1",
        target_condition={"phase": "secure"},
        target_perception_id="another-perception",
    )

    result = DefaultGoalFeasibilityTool().evaluate(goal, projected)

    assert result.reachable is False
    assert result.confidence == 0.0
    assert result.metadata["reason"] == "target_perception_id_mismatch"


def test_default_goal_feasibility_tool_empty_target_condition_not_reachable():
    projected = _build_projected_state()
    goal = Goal(
        id="goal-5",
        actor_id="actor-1",
        target_condition={},
    )

    result = DefaultGoalFeasibilityTool().evaluate(goal, projected)

    assert result.reachable is False
    assert result.confidence == 0.0
    assert result.metadata["reason"] == "empty_target_condition"


def test_goal_admissibility_checker_accepts_valid_goal():
    goal = Goal(
        id="goal-a-1",
        actor_id="actor-1",
        target_condition={"phase": "secure"},
        horizon={"max_steps": 2},
    )
    actor = Actor(id="actor-1")
    actor.add_goal(goal.id)
    perception = Perception(
        id="perception-a-1",
        actor_id="actor-1",
        source_id="world-1",
        context={"available_projection_steps": 4},
    )

    result = GoalAdmissibilityChecker().check(goal, actor, perception)

    assert result.admissible is True
    assert result.reason == "admissible"
    assert result.blocking_constraints == []


def test_goal_admissibility_checker_rejects_goal_actor_mismatch():
    goal = Goal(
        id="goal-a-2",
        actor_id="actor-2",
        target_condition={"phase": "secure"},
    )
    actor = Actor(id="actor-1")
    actor.add_goal(goal.id)
    perception = Perception(
        id="perception-a-2",
        actor_id="actor-1",
        source_id="world-1",
    )

    result = GoalAdmissibilityChecker().check(goal, actor, perception)

    assert result.admissible is False
    assert result.reason == "goal_actor_mismatch"


def test_goal_admissibility_checker_rejects_goal_not_linked_to_actor():
    goal = Goal(
        id="goal-a-3",
        actor_id="actor-1",
        target_condition={"phase": "secure"},
    )
    actor = Actor(id="actor-1")
    perception = Perception(
        id="perception-a-3",
        actor_id="actor-1",
        source_id="world-1",
    )

    result = GoalAdmissibilityChecker().check(goal, actor, perception)

    assert result.admissible is False
    assert result.reason == "goal_not_linked_to_actor"


def test_goal_admissibility_checker_rejects_blocking_constraints():
    goal = Goal(
        id="goal-a-4",
        actor_id="actor-1",
        target_condition={"phase": "secure"},
    )
    actor = Actor(id="actor-1")
    actor.add_goal(goal.id)
    actor.add_constraint("constraint-1")
    actor.add_constraint("constraint-2")
    perception = Perception(
        id="perception-a-4",
        actor_id="actor-1",
        source_id="world-1",
        context={
            "blocked_constraints": [
                "constraint-2",
                "constraint-99",
            ]
        },
    )

    result = GoalAdmissibilityChecker().check(goal, actor, perception)

    assert result.admissible is False
    assert result.reason == "blocked_by_constraints"
    assert result.blocking_constraints == ["constraint-2"]


def test_goal_admissibility_checker_rejects_insufficient_projection_capacity():
    goal = Goal(
        id="goal-a-5",
        actor_id="actor-1",
        target_condition={"phase": "secure"},
        horizon={"max_steps": 5},
    )
    actor = Actor(id="actor-1")
    actor.add_goal(goal.id)
    perception = Perception(
        id="perception-a-5",
        actor_id="actor-1",
        source_id="world-1",
        context={"available_projection_steps": 2},
    )

    result = GoalAdmissibilityChecker().check(goal, actor, perception)

    assert result.admissible is False
    assert result.reason == "insufficient_projection_capacity"


def test_goal_result_serialization_helpers():
    feasibility = GoalFeasibilityResult(
        reachable=True,
        confidence=1.0,
        matching_keys=["b", "a"],
        metadata={"k": "v"},
    )
    admissibility = GoalAdmissibilityResult(
        admissible=False,
        reason="blocked_by_constraints",
        blocking_constraints=["c2", "c1"],
    )

    feasibility_payload = feasibility.to_dict()
    admissibility_payload = admissibility.to_dict()

    assert feasibility_payload["matching_keys"] == ["a", "b"]
    assert admissibility_payload["blocking_constraints"] == [
        "c1",
        "c2",
    ]
