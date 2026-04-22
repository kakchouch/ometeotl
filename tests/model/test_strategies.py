"""Tests for masm.model.strategies."""

import pytest

from masm.model.actions import Action
from masm.model.perception import Perception
from masm.model.projection import DefaultProjectionTool
from masm.model.strategies import (
    Strategy,
    StrategyBuildStep,
    StrategyNode,
    StrategyOutcomeBranch,
    build_branching_strategy,
    build_linear_strategy,
)


def test_strategy_instantiation():
    """Verify that strategy objects instantiate with required fields."""
    root_projection = DefaultProjectionTool().project_action(
        Action(
            id="action-1",
            actor_id="actor-1",
            world_id="world-1",
            space_id="space-1",
            action_type="move",
        ),
        Perception(
            id="perception-root",
            actor_id="actor-1",
            source_id="world-1",
        ),
    )
    strategy = Strategy(
        id="strategy-1",
        actor_id="actor-1",
        root_node_id="node-root",
        nodes=[
            StrategyNode(
                node_id="node-root",
                action_id="action-1",
                source_perception_id="perception-root",
                projected_state=root_projection.projected_state,
                outcome_branches=[
                    StrategyOutcomeBranch(
                        branch_id="success",
                        label="success",
                    )
                ],
            )
        ],
    )

    assert strategy.id == "strategy-1"
    assert strategy.object_type == "strategy"
    assert strategy.actor_id == "actor-1"
    assert strategy.goal_id is None
    assert strategy.root_node_id == "node-root"
    assert strategy.projection_policy == "perception_first"
    assert len(strategy.nodes) == 1
    assert strategy.nodes[0].source_perception_id == "perception-root"
    assert (
        strategy.nodes[0].successor_perception_id
        == "projection-perception-root-action-1"
    )


def test_strategy_serialization_is_deterministic():
    """Verify deterministic ordering of nodes and branches in strategy export."""
    root_projection = DefaultProjectionTool().project_action(
        Action(
            id="action-1",
            actor_id="actor-1",
            world_id="world-1",
            space_id="space-1",
            action_type="move",
        ),
        Perception(
            id="perception-chain-root",
            actor_id="actor-1",
            source_id="world-1",
        ),
    )
    root_projected_state = root_projection.projected_state
    assert root_projected_state is not None
    strategy = Strategy(
        id="strategy-2",
        actor_id="actor-1",
        root_node_id="node-a",
        nodes=[
            StrategyNode(
                node_id="node-b",
                action_id="action-2",
                source_perception_id=root_projected_state.perception.id,
                outcome_branches=[
                    StrategyOutcomeBranch(
                        branch_id="z",
                        label="late",
                        child_node_id="node-a",
                    ),
                    StrategyOutcomeBranch(
                        branch_id="a",
                        label="early",
                        child_node_id="node-a",
                    ),
                ],
            ),
            StrategyNode(
                node_id="node-a",
                action_id="action-1",
                source_perception_id="perception-chain-root",
                projected_state=root_projected_state,
            ),
        ],
    )

    payload = strategy.to_dict()
    restored = Strategy.from_dict(payload)

    assert [node["node_id"] for node in payload["nodes"]] == ["node-a", "node-b"]
    assert payload["goal_id"] is None
    assert payload["nodes"][0]["source_perception_id"] == "perception-chain-root"
    assert (
        payload["nodes"][0]["projected_state"]["perception"]["id"]
        == "projection-perception-chain-root-action-1"
    )
    assert [
        branch["branch_id"] for branch in payload["nodes"][1]["outcome_branches"]
    ] == ["a", "z"]
    assert restored.to_dict() == payload


def test_strategy_serialization_supports_goal_linkage():
    """A strategy may optionally reference a goal through goal_id."""
    strategy = Strategy(
        id="strategy-with-goal",
        actor_id="actor-1",
        goal_id="goal-1",
        root_node_id="node-root",
        nodes=[
            StrategyNode(
                node_id="node-root",
                action_id="action-1",
            )
        ],
    )

    payload = strategy.to_dict()
    restored = Strategy.from_dict(payload)

    assert payload["goal_id"] == "goal-1"
    assert restored.goal_id == "goal-1"


def test_strategy_from_dict_defaults_goal_id_to_none_when_missing():
    """Backwards compatibility: strategies without goal_id deserialize with None."""
    data = {
        "id": "strategy-no-goal",
        "object_type": "strategy",
        "schema_version": "1.0",
        "attributes": {},
        "relations": {},
        "state": {},
        "context": {},
        "provenance": {},
        "actor_id": "actor-1",
        "root_node_id": "node-root",
        "nodes": [
            {
                "node_id": "node-root",
                "action_id": "action-1",
                "source_perception_id": None,
                "projected_state": None,
                "outcome_branches": [],
                "metadata": {},
            }
        ],
        "projection_policy": "perception_first",
    }

    strategy = Strategy.from_dict(data)
    assert strategy.goal_id is None


def test_strategy_validate_tree_rejects_unknown_child_node():
    """Verify that tree validation rejects branches to unknown child nodes."""
    strategy = Strategy(
        id="strategy-3",
        actor_id="actor-1",
        root_node_id="node-a",
        nodes=[
            StrategyNode(
                node_id="node-a",
                action_id="action-1",
                outcome_branches=[
                    StrategyOutcomeBranch(
                        branch_id="failure",
                        child_node_id="node-missing",
                    )
                ],
            )
        ],
    )

    with pytest.raises(ValueError, match="child_node_id"):
        strategy.validate_tree()


def test_strategy_validate_tree_rejects_child_not_chained_to_parent_projection():
    """Child nodes must start from the parent projected successor perception."""
    root_projection = DefaultProjectionTool().project_action(
        Action(
            id="action-root",
            actor_id="actor-1",
            world_id="world-1",
            space_id="space-1",
            action_type="move",
        ),
        Perception(
            id="perception-strategy-root",
            actor_id="actor-1",
            source_id="world-1",
        ),
    )
    root_projected_state = root_projection.projected_state
    assert root_projected_state is not None
    strategy = Strategy(
        id="strategy-4",
        actor_id="actor-1",
        root_node_id="node-root",
        nodes=[
            StrategyNode(
                node_id="node-root",
                action_id="action-root",
                source_perception_id="perception-strategy-root",
                projected_state=root_projected_state,
                outcome_branches=[
                    StrategyOutcomeBranch(
                        branch_id="success",
                        child_node_id="node-child",
                    )
                ],
            ),
            StrategyNode(
                node_id="node-child",
                action_id="action-child",
                source_perception_id="perception-wrong",
            ),
        ],
    )

    with pytest.raises(ValueError, match="consume the parent projected perception"):
        strategy.validate_tree()


def test_strategy_validate_tree_accepts_child_chained_to_parent_projection():
    """Child nodes can explicitly consume the parent successor projected perception."""
    root_projection = DefaultProjectionTool().project_action(
        Action(
            id="action-root-ok",
            actor_id="actor-1",
            world_id="world-1",
            space_id="space-1",
            action_type="move",
        ),
        Perception(
            id="perception-strategy-ok-root",
            actor_id="actor-1",
            source_id="world-1",
        ),
    )
    root_projected_state = root_projection.projected_state
    assert root_projected_state is not None
    strategy = Strategy(
        id="strategy-5",
        actor_id="actor-1",
        root_node_id="node-root",
        nodes=[
            StrategyNode(
                node_id="node-root",
                action_id="action-root-ok",
                source_perception_id="perception-strategy-ok-root",
                projected_state=root_projected_state,
                outcome_branches=[
                    StrategyOutcomeBranch(
                        branch_id="success",
                        child_node_id="node-child",
                    )
                ],
            ),
            StrategyNode(
                node_id="node-child",
                action_id="action-child-ok",
                source_perception_id=root_projected_state.perception.id,
            ),
        ],
    )

    strategy.validate_tree()


def test_build_linear_strategy_chains_nodes_from_ordered_actions_sequence():
    """A linear builder chains each node from the previous projected perception."""
    initial_perception = Perception(
        id="perception-build-root",
        actor_id="actor-1",
        source_id="world-1",
    )
    actions = [
        Action(
            id="action-build-1",
            actor_id="actor-1",
            world_id="world-1",
            space_id="space-1",
            action_type="move",
            state_changes={"context_updates": {"step": 1}},
        ),
        Action(
            id="action-build-2",
            actor_id="actor-1",
            world_id="world-1",
            space_id="space-1",
            action_type="observe",
            state_changes={"context_updates": {"step": 2}},
        ),
    ]

    strategy = build_linear_strategy(
        "strategy-linear-1",
        initial_perception,
        actions,
    )

    assert strategy.root_node_id == "node-0001-action-build-1"
    assert [node.node_id for node in strategy.nodes] == [
        "node-0001-action-build-1",
        "node-0002-action-build-2",
    ]
    assert strategy.nodes[0].source_perception_id == "perception-build-root"
    assert (
        strategy.nodes[1].source_perception_id
        == strategy.nodes[0].successor_perception_id
    )
    assert (
        strategy.nodes[0].outcome_branches[0].child_node_id
        == "node-0002-action-build-2"
    )
    assert strategy.nodes[1].projected_state is not None
    assert strategy.nodes[1].projected_state.perception.context["step"] == 2


def test_build_linear_strategy_rejects_empty_action_sequence():
    """The linear builder requires at least one action."""
    with pytest.raises(ValueError, match="at least one action"):
        build_linear_strategy(
            "strategy-linear-empty",
            Perception(
                id="perception-empty",
                actor_id="actor-1",
                source_id="world-1",
            ),
            [],
        )


def test_build_linear_strategy_rejects_blocked_projection_chain():
    """The linear builder rejects sequences that cannot produce a successor perception."""
    with pytest.raises(
        ValueError,
        match="cannot continue without a projected successor perception",
    ):
        build_linear_strategy(
            "strategy-linear-blocked",
            Perception(
                id="perception-blocked",
                actor_id="actor-1",
                source_id="world-1",
            ),
            [
                Action(
                    id="action-blocked",
                    actor_id="actor-2",
                    world_id="world-1",
                    space_id="space-1",
                    action_type="move",
                )
            ],
        )


def test_build_branching_strategy_creates_tree_from_recursive_steps():
    """The branching builder creates sibling children from one projected parent state."""
    strategy = build_branching_strategy(
        "strategy-branch-1",
        Perception(
            id="perception-branch-root",
            actor_id="actor-1",
            source_id="world-1",
        ),
        StrategyBuildStep(
            action=Action(
                id="action-root-branch",
                actor_id="actor-1",
                world_id="world-1",
                space_id="space-1",
                action_type="plan",
                state_changes={"context_updates": {"phase": "root"}},
            ),
            children=[
                StrategyBuildStep(
                    action=Action(
                        id="action-left-branch",
                        actor_id="actor-1",
                        world_id="world-1",
                        space_id="space-1",
                        action_type="explore",
                        state_changes={"context_updates": {"phase": "left"}},
                    ),
                    branch_label="left",
                    branch_probability=0.4,
                    branch_condition={"signal": "weak"},
                ),
                StrategyBuildStep(
                    action=Action(
                        id="action-right-branch",
                        actor_id="actor-1",
                        world_id="world-1",
                        space_id="space-1",
                        action_type="secure",
                        state_changes={"context_updates": {"phase": "right"}},
                    ),
                    branch_label="right",
                    branch_probability=0.6,
                    branch_condition={"signal": "strong"},
                ),
            ],
        ),
    )

    root_node = strategy.get_node("node-0001-action-root-branch")
    left_node = strategy.get_node("node-0001-0001-action-left-branch")
    right_node = strategy.get_node("node-0001-0002-action-right-branch")

    assert root_node is not None
    assert left_node is not None
    assert right_node is not None
    assert len(root_node.outcome_branches) == 2
    assert [branch.label for branch in root_node.outcome_branches] == ["left", "right"]
    assert left_node.source_perception_id == root_node.successor_perception_id
    assert right_node.source_perception_id == root_node.successor_perception_id
    assert left_node.projected_state is not None
    assert right_node.projected_state is not None
    assert left_node.projected_state.perception.context["phase"] == "left"
    assert right_node.projected_state.perception.context["phase"] == "right"


def test_build_branching_strategy_rejects_blocked_child_step():
    """The branching builder fails when any child step cannot project a successor."""
    with pytest.raises(
        ValueError,
        match="build_branching_strategy cannot continue without a projected successor perception",
    ):
        build_branching_strategy(
            "strategy-branch-blocked",
            Perception(
                id="perception-branch-blocked",
                actor_id="actor-1",
                source_id="world-1",
            ),
            StrategyBuildStep(
                action=Action(
                    id="action-branch-root-ok",
                    actor_id="actor-1",
                    world_id="world-1",
                    space_id="space-1",
                    action_type="plan",
                ),
                children=[
                    StrategyBuildStep(
                        action=Action(
                            id="action-branch-child-blocked",
                            actor_id="actor-2",
                            world_id="world-1",
                            space_id="space-1",
                            action_type="move",
                        ),
                        branch_label="blocked-child",
                    )
                ],
            ),
        )
