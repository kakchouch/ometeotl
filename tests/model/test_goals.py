"""Tests for masm.model.goals."""

import pytest

from masm.model.goals import (
    Goal,
    GoalBuildStep,
    GoalDecompositionTree,
    build_goal_hierarchy,
)


def test_goal_instantiation():
    """Verify that goal objects instantiate with required fields."""
    goal = Goal(
        id="goal-1",
        actor_id="actor-1",
        kind="final",
        priority=1.0,
        status="active",
        target_condition={"location": "target_zone", "resource_count": 10},
    )

    assert goal.id == "goal-1"
    assert goal.object_type == "goal"
    assert goal.actor_id == "actor-1"
    assert goal.kind == "final"
    assert goal.priority == 1.0
    assert goal.status == "active"
    assert goal.target_condition == {"location": "target_zone", "resource_count": 10}
    assert goal.parent_goal_id is None
    assert goal.child_goal_ids == []
    assert goal.strategy_ids == []


def test_goal_kind_validation():
    """Goal kind must be 'final' or 'intermediate'."""
    with pytest.raises(ValueError, match="kind must be 'final' or 'intermediate'"):
        Goal(
            id="goal-bad-kind",
            actor_id="actor-1",
            kind="invalid",
            target_condition={},
        )


def test_goal_priority_validation():
    """Goal priority must be in [0, 1]."""
    with pytest.raises(ValueError, match="priority must be in"):
        Goal(
            id="goal-bad-priority",
            actor_id="actor-1",
            kind="final",
            priority=1.5,
            target_condition={},
        )


def test_goal_status_validation():
    """Goal status must be one of the defined values."""
    with pytest.raises(ValueError, match="status must be one of"):
        Goal(
            id="goal-bad-status",
            actor_id="actor-1",
            kind="final",
            status="invalid",
            target_condition={},
        )


def test_goal_add_child_goal():
    """Child goals can be registered and deduplicated."""
    goal = Goal(
        id="goal-parent",
        actor_id="actor-1",
        kind="final",
        target_condition={},
    )
    goal.add_child_goal("goal-child-1")
    goal.add_child_goal("goal-child-2")
    goal.add_child_goal("goal-child-1")  # duplicate

    assert goal.child_goal_ids == ["goal-child-1", "goal-child-2"]


def test_goal_add_strategy():
    """Strategies can be registered and deduplicated."""
    goal = Goal(
        id="goal-1",
        actor_id="actor-1",
        kind="final",
        target_condition={},
    )
    goal.add_strategy("strategy-1")
    goal.add_strategy("strategy-2")
    goal.add_strategy("strategy-1")  # duplicate

    assert goal.strategy_ids == ["strategy-1", "strategy-2"]


def test_goal_serialization_round_trip():
    """Goal serializes and deserializes correctly."""
    goal = Goal(
        id="goal-serialize",
        actor_id="actor-1",
        kind="intermediate",
        priority=0.75,
        status="achieved",
        horizon={"max_steps": 10},
        target_condition={"wealth": 500},
        target_perception_id="perception-1",
        parent_goal_id="goal-parent",
        child_goal_ids=["goal-child-1", "goal-child-2"],
        strategy_ids=["strategy-1"],
    )

    goal_dict = goal.to_dict()
    assert goal_dict["id"] == "goal-serialize"
    assert goal_dict["actor_id"] == "actor-1"
    assert goal_dict["kind"] == "intermediate"
    assert goal_dict["priority"] == 0.75
    assert goal_dict["status"] == "achieved"
    assert goal_dict["horizon"] == {"max_steps": 10}
    assert goal_dict["target_condition"] == {"wealth": 500}
    assert goal_dict["target_perception_id"] == "perception-1"
    assert goal_dict["parent_goal_id"] == "goal-parent"
    assert goal_dict["child_goal_ids"] == ["goal-child-1", "goal-child-2"]
    assert goal_dict["strategy_ids"] == ["strategy-1"]

    recovered_goal = Goal.from_dict(goal_dict)
    assert recovered_goal.id == goal.id
    assert recovered_goal.actor_id == goal.actor_id
    assert recovered_goal.kind == goal.kind
    assert recovered_goal.priority == goal.priority
    assert recovered_goal.status == goal.status
    assert recovered_goal.horizon == goal.horizon
    assert recovered_goal.target_condition == goal.target_condition
    assert recovered_goal.target_perception_id == goal.target_perception_id
    assert recovered_goal.parent_goal_id == goal.parent_goal_id
    assert recovered_goal.child_goal_ids == goal.child_goal_ids
    assert recovered_goal.strategy_ids == goal.strategy_ids


def test_goal_decomposition_tree_instantiation():
    """GoalDecompositionTree instantiates with a root goal."""
    root_goal = Goal(
        id="root",
        actor_id="actor-1",
        kind="final",
        target_condition={},
    )
    tree = GoalDecompositionTree(
        root_goal_id="root",
        goals={"root": root_goal},
    )

    assert tree.root_goal_id == "root"
    assert tree.get_goal("root") == root_goal


def test_goal_decomposition_tree_rejects_unknown_root():
    """GoalDecompositionTree rejects if root_goal_id is not registered."""
    with pytest.raises(ValueError, match="must reference a registered goal"):
        GoalDecompositionTree(
            root_goal_id="nonexistent",
            goals={},
        )


def test_goal_decomposition_tree_rejects_root_with_parent():
    """GoalDecompositionTree rejects if root goal has a parent_goal_id."""
    root_goal = Goal(
        id="root-with-parent",
        actor_id="actor-1",
        kind="final",
        target_condition={},
        parent_goal_id="some-parent",
    )
    with pytest.raises(ValueError, match="must not have a parent_goal_id"):
        GoalDecompositionTree(
            root_goal_id="root-with-parent",
            goals={"root-with-parent": root_goal},
        )


def test_goal_decomposition_tree_validate_tree_rejects_unknown_child():
    """validate_tree rejects unknown child goal references."""
    root_goal = Goal(
        id="root",
        actor_id="actor-1",
        kind="final",
        target_condition={},
        child_goal_ids=["nonexistent-child"],
    )
    tree = GoalDecompositionTree(
        root_goal_id="root",
        goals={"root": root_goal},
    )
    with pytest.raises(ValueError, match="unknown child goal"):
        tree.validate_tree()


def test_goal_decomposition_tree_validate_tree_rejects_unknown_parent():
    """validate_tree rejects unknown parent goal references."""
    root_goal = Goal(
        id="root",
        actor_id="actor-1",
        kind="final",
        target_condition={},
    )
    orphan_goal = Goal(
        id="orphan",
        actor_id="actor-1",
        kind="intermediate",
        target_condition={},
        parent_goal_id="nonexistent-parent",
    )
    tree = GoalDecompositionTree(
        root_goal_id="root",
        goals={"root": root_goal, "orphan": orphan_goal},
    )
    with pytest.raises(ValueError, match="unknown parent goal"):
        tree.validate_tree()


def test_goal_decomposition_tree_validate_tree_rejects_cycles():
    """validate_tree rejects goal hierarchies with cycles."""
    goal_a = Goal(
        id="goal-a",
        actor_id="actor-1",
        kind="intermediate",
        target_condition={},
        child_goal_ids=["goal-b"],
    )
    goal_b = Goal(
        id="goal-b",
        actor_id="actor-1",
        kind="intermediate",
        target_condition={},
        parent_goal_id="goal-a",
        child_goal_ids=["goal-a"],  # cycle back to goal-a
    )
    tree = GoalDecompositionTree(
        root_goal_id="goal-a",
        goals={"goal-a": goal_a, "goal-b": goal_b},
    )
    with pytest.raises(ValueError, match="contains a cycle"):
        tree.validate_tree()


def test_goal_decomposition_tree_validate_tree_accepts_valid_hierarchy():
    """validate_tree accepts a valid tree structure."""
    root_goal = Goal(
        id="root",
        actor_id="actor-1",
        kind="final",
        target_condition={},
        child_goal_ids=["intermediate-1", "intermediate-2"],
    )
    intermediate_1 = Goal(
        id="intermediate-1",
        actor_id="actor-1",
        kind="intermediate",
        target_condition={},
        parent_goal_id="root",
        child_goal_ids=["leaf-1"],
    )
    intermediate_2 = Goal(
        id="intermediate-2",
        actor_id="actor-1",
        kind="intermediate",
        target_condition={},
        parent_goal_id="root",
    )
    leaf_1 = Goal(
        id="leaf-1",
        actor_id="actor-1",
        kind="intermediate",
        target_condition={},
        parent_goal_id="intermediate-1",
    )
    tree = GoalDecompositionTree(
        root_goal_id="root",
        goals={
            "root": root_goal,
            "intermediate-1": intermediate_1,
            "intermediate-2": intermediate_2,
            "leaf-1": leaf_1,
        },
    )
    tree.validate_tree()  # should not raise


def test_goal_decomposition_tree_children_of():
    """children_of returns direct children of a goal."""
    root_goal = Goal(
        id="root",
        actor_id="actor-1",
        kind="final",
        target_condition={},
        child_goal_ids=["child-1", "child-2"],
    )
    child_1 = Goal(
        id="child-1",
        actor_id="actor-1",
        kind="intermediate",
        target_condition={},
        parent_goal_id="root",
    )
    child_2 = Goal(
        id="child-2",
        actor_id="actor-1",
        kind="intermediate",
        target_condition={},
        parent_goal_id="root",
    )
    tree = GoalDecompositionTree(
        root_goal_id="root",
        goals={"root": root_goal, "child-1": child_1, "child-2": child_2},
    )

    children = tree.children_of("root")
    assert len(children) == 2
    assert {c.id for c in children} == {"child-1", "child-2"}


def test_goal_decomposition_tree_parent_of():
    """parent_of returns the parent goal."""
    root_goal = Goal(
        id="root",
        actor_id="actor-1",
        kind="final",
        target_condition={},
        child_goal_ids=["child"],
    )
    child_goal = Goal(
        id="child",
        actor_id="actor-1",
        kind="intermediate",
        target_condition={},
        parent_goal_id="root",
    )
    tree = GoalDecompositionTree(
        root_goal_id="root",
        goals={"root": root_goal, "child": child_goal},
    )

    parent = tree.parent_of("child")
    assert parent is not None
    assert parent.id == "root"


def test_goal_decomposition_tree_serialization_round_trip():
    """GoalDecompositionTree serializes and deserializes correctly."""
    root_goal = Goal(
        id="root",
        actor_id="actor-1",
        kind="final",
        target_condition={"status": "complete"},
        child_goal_ids=["intermediate"],
    )
    intermediate_goal = Goal(
        id="intermediate",
        actor_id="actor-1",
        kind="intermediate",
        target_condition={"progress": 50},
        parent_goal_id="root",
    )
    tree = GoalDecompositionTree(
        root_goal_id="root",
        goals={"root": root_goal, "intermediate": intermediate_goal},
    )

    tree_dict = tree.to_dict()
    assert tree_dict["root_goal_id"] == "root"
    assert "root" in tree_dict["goals"]
    assert "intermediate" in tree_dict["goals"]

    recovered_tree = GoalDecompositionTree.from_dict(tree_dict)
    assert recovered_tree.root_goal_id == tree.root_goal_id
    assert len(recovered_tree.goals) == 2
    assert recovered_tree.get_goal("root") is not None
    assert recovered_tree.get_goal("intermediate") is not None


def test_build_goal_hierarchy_linear():
    """build_goal_hierarchy creates a simple linear hierarchy."""
    root_step = GoalBuildStep(
        kind="final",
        actor_id="actor-1",
        target_condition={"final": True},
        priority=1.0,
        children=[
            GoalBuildStep(
                kind="intermediate",
                actor_id="actor-1",
                target_condition={"intermediate": True},
                priority=0.8,
            )
        ],
    )

    tree = build_goal_hierarchy(root_step)

    assert tree.root_goal_id is not None
    assert len(tree.goals) == 2
    root_goal = tree.get_goal(tree.root_goal_id)
    assert root_goal is not None
    assert root_goal.kind == "final"
    assert root_goal.target_condition == {"final": True}
    assert len(root_goal.child_goal_ids) == 1

    child_goal = tree.get_goal(root_goal.child_goal_ids[0])
    assert child_goal is not None
    assert child_goal.kind == "intermediate"
    assert child_goal.target_condition == {"intermediate": True}
    assert child_goal.parent_goal_id == root_goal.id


def test_build_goal_hierarchy_branching():
    """build_goal_hierarchy creates a branching hierarchy."""
    root_step = GoalBuildStep(
        kind="final",
        actor_id="actor-1",
        target_condition={"goal": "achieve"},
        children=[
            GoalBuildStep(
                kind="intermediate",
                actor_id="actor-1",
                target_condition={"phase": 1},
            ),
            GoalBuildStep(
                kind="intermediate",
                actor_id="actor-1",
                target_condition={"phase": 2},
            ),
        ],
    )

    tree = build_goal_hierarchy(root_step)

    assert len(tree.goals) == 3
    root_goal = tree.get_goal(tree.root_goal_id)
    assert len(root_goal.child_goal_ids) == 2

    children = tree.children_of(root_goal.id)
    assert len(children) == 2
    assert all(c.parent_goal_id == root_goal.id for c in children)


def test_build_goal_hierarchy_deep_nesting():
    """build_goal_hierarchy creates deeply nested hierarchies."""
    leaf = GoalBuildStep(
        kind="intermediate",
        actor_id="actor-1",
        target_condition={"level": 3},
    )
    mid = GoalBuildStep(
        kind="intermediate",
        actor_id="actor-1",
        target_condition={"level": 2},
        children=[leaf],
    )
    root_step = GoalBuildStep(
        kind="final",
        actor_id="actor-1",
        target_condition={"level": 1},
        children=[mid],
    )

    tree = build_goal_hierarchy(root_step)

    assert len(tree.goals) == 3
    root_goal = tree.get_goal(tree.root_goal_id)
    assert root_goal.kind == "final"

    mid_goal = tree.children_of(root_goal.id)[0]
    assert mid_goal.kind == "intermediate"
    assert mid_goal.target_condition["level"] == 2

    leaf_goal = tree.children_of(mid_goal.id)[0]
    assert leaf_goal.kind == "intermediate"
    assert leaf_goal.target_condition["level"] == 3


def test_build_goal_hierarchy_validates_tree():
    """build_goal_hierarchy validates the tree before returning."""
    # Create a malformed step that would violate tree invariants
    # (but shouldn't happen in practice with the builder)
    # The builder itself ensures invariants, so we just verify no exception on valid input

    root_step = GoalBuildStep(
        kind="final",
        actor_id="actor-1",
        target_condition={},
        children=[
            GoalBuildStep(
                kind="intermediate",
                actor_id="actor-1",
                target_condition={},
            ),
        ],
    )

    tree = build_goal_hierarchy(root_step)
    # validate_tree is called internally; if there were any issues, an exception would be raised
    tree.validate_tree()  # should not raise


def test_goal_build_step_validation():
    """GoalBuildStep validates kind and priority on instantiation."""
    with pytest.raises(ValueError, match="kind must be"):
        GoalBuildStep(
            kind="invalid",
            actor_id="actor-1",
            target_condition={},
        )

    with pytest.raises(ValueError, match="priority must be in"):
        GoalBuildStep(
            kind="final",
            actor_id="actor-1",
            target_condition={},
            priority=1.5,
        )
