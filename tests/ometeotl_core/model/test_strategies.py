"""Tests for ometeotl_core.model.strategies."""

import pytest

from ometeotl_core.model.actions import Action
from ometeotl_core.model.perception import Perception
from ometeotl_core.model.projection import DefaultProjectionTool
from ometeotl_core.model.strategies import (
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
                outcome_branches=[
                    StrategyOutcomeBranch(
                        branch_id="success",
                        label="success",
                        projected_state=root_projection.projected_state,
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
        strategy.nodes[0].outcome_branches[0].projected_state.perception.id
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
                    ),
                    StrategyOutcomeBranch(
                        branch_id="a",
                        label="early",
                    ),
                ],
            ),
            StrategyNode(
                node_id="node-a",
                action_id="action-1",
                source_perception_id="perception-chain-root",
                outcome_branches=[
                    StrategyOutcomeBranch(
                        branch_id="success",
                        child_node_id="node-b",
                        projected_state=root_projected_state,
                    )
                ],
            ),
        ],
    )

    payload = strategy.to_dict()
    restored = Strategy.from_dict(payload)

    assert [node["node_id"] for node in payload["nodes"]] == [
        "node-a",
        "node-b",
    ]
    assert payload["goal_id"] is None
    assert payload["nodes"][0]["source_perception_id"] == "perception-chain-root"
    assert (
        payload["nodes"][0]["outcome_branches"][0]["projected_state"]["perception"]["id"]
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
    """Child nodes must start from the branch projected successor perception."""
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
                outcome_branches=[
                    StrategyOutcomeBranch(
                        branch_id="success",
                        child_node_id="node-child",
                        projected_state=root_projected_state,
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

    with pytest.raises(
        ValueError,
        match="consume the branch projected perception",
    ):
        strategy.validate_tree()


def test_strategy_validate_tree_accepts_child_chained_to_parent_projection():
    """Child nodes can explicitly consume the branch successor projected perception."""
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
                outcome_branches=[
                    StrategyOutcomeBranch(
                        branch_id="success",
                        child_node_id="node-child",
                        projected_state=root_projected_state,
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
    success_branch = strategy.nodes[0].outcome_branches[0]
    assert success_branch.child_node_id == "node-0002-action-build-2"
    assert success_branch.projected_state is not None
    assert (
        strategy.nodes[1].source_perception_id
        == success_branch.projected_state.perception.id
    )
    assert success_branch.projected_state.perception.context["step"] == 1
    # terminal node has one terminal branch (no child, carries the projected outcome)
    assert len(strategy.nodes[1].outcome_branches) == 1
    terminal_branch = strategy.nodes[1].outcome_branches[0]
    assert terminal_branch.child_node_id is None
    assert terminal_branch.projected_state is not None
    assert terminal_branch.projected_state.perception.context["step"] == 2


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
    assert [branch.label for branch in root_node.outcome_branches] == [
        "left",
        "right",
    ]
    left_branch = root_node.outcome_branches[0]
    right_branch = root_node.outcome_branches[1]

    # branches carry the root action's projected state (deterministic projection)
    assert left_branch.projected_state is not None
    assert right_branch.projected_state is not None

    # child nodes consume the branch projected perception
    assert left_node.source_perception_id == left_branch.projected_state.perception.id
    assert right_node.source_perception_id == right_branch.projected_state.perception.id

    # leaf nodes each have one terminal branch (no child, carries projected outcome)
    assert len(left_node.outcome_branches) == 1
    assert left_node.outcome_branches[0].child_node_id is None
    assert left_node.outcome_branches[0].projected_state is not None
    assert len(right_node.outcome_branches) == 1
    assert right_node.outcome_branches[0].child_node_id is None
    assert right_node.outcome_branches[0].projected_state is not None


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


def test_strategy_from_context_builds_strategy_with_structural_validation():
    strategy = Strategy.from_context(
        {
            "id": "strategy-ctx-1",
            "actor_id": "actor-ctx-1",
            "goal_id": "goal-ctx-1",
            "root_node_id": "node-root-ctx",
            "action_id": "action-ctx-1",
            "projection_policy": "perception_first",
            "validate": False,
        }
    )

    assert isinstance(strategy, Strategy)
    assert strategy.id == "strategy-ctx-1"
    assert strategy.actor_id == "actor-ctx-1"
    assert strategy.goal_id == "goal-ctx-1"
    assert strategy.root_node_id == "node-root-ctx"
    assert strategy.projection_policy == "perception_first"
    assert len(strategy.nodes) == 1
    assert strategy.nodes[0].node_id == "node-root-ctx"


def test_strategy_from_context_requires_non_empty_id():
    with pytest.raises(ValueError, match="requires non-empty 'id'"):
        Strategy.from_context({"actor_id": "actor-1"})


def test_strategy_from_context_forwards_validate_flag(monkeypatch):
    import ometeotl_core.generation as generation_module

    class _DummyPipeline:
        def __init__(self, *, validation_pipeline):
            del validation_pipeline

        def generate(self, generation_context):
            assert generation_context.validate is False

            class _Result:
                generated = Strategy(
                    id="strategy-ctx-forward-1",
                    actor_id="actor-1",
                    root_node_id="root",
                    nodes=[StrategyNode(node_id="root", action_id="action-1")],
                )
                validation = None

            return _Result()

    monkeypatch.setattr(
        generation_module,
        "ContextualGenerationPipeline",
        _DummyPipeline,
    )

    strategy = Strategy.from_context(
        {
            "id": "strategy-ctx-forward-1",
            "actor_id": "actor-1",
            "action_id": "action-1",
            "validate": False,
        }
    )

    assert isinstance(strategy, Strategy)
    assert strategy.id == "strategy-ctx-forward-1"


# ---------------------------------------------------------------------------
# New tests for branch-level projected states (one-action-to-many-outcomes)
# ---------------------------------------------------------------------------


def test_strategy_outcome_branch_carries_projected_state():
    """StrategyOutcomeBranch stores and round-trips its projected_state."""
    projection = DefaultProjectionTool().project_action(
        Action(
            id="action-branch-ps",
            actor_id="actor-1",
            world_id="world-1",
            space_id="space-1",
            action_type="move",
        ),
        Perception(
            id="perception-branch-ps-root",
            actor_id="actor-1",
            source_id="world-1",
        ),
    )
    projected_state = projection.projected_state
    assert projected_state is not None

    branch = StrategyOutcomeBranch(
        branch_id="outcome-a",
        label="outcome-a",
        projected_state=projected_state,
    )

    payload = branch.to_dict()
    assert payload["projected_state"] is not None
    assert (
        payload["projected_state"]["perception"]["id"]
        == "projection-perception-branch-ps-root-action-branch-ps"
    )

    restored = StrategyOutcomeBranch.from_dict(payload)
    assert restored.projected_state is not None
    assert (
        restored.projected_state.perception.id
        == projected_state.perception.id
    )


def test_strategy_outcome_branch_without_projected_state_serializes_null():
    """A branch without projected_state serializes projected_state as null."""
    branch = StrategyOutcomeBranch(branch_id="bare-branch", label="success")
    payload = branch.to_dict()
    assert payload["projected_state"] is None
    restored = StrategyOutcomeBranch.from_dict(payload)
    assert restored.projected_state is None


def test_strategy_validate_tree_rejects_branch_projected_state_wrong_action():
    """validate_tree rejects a branch whose projected_state was not generated by the parent action."""
    projection = DefaultProjectionTool().project_action(
        Action(
            id="action-other",
            actor_id="actor-1",
            world_id="world-1",
            space_id="space-1",
            action_type="move",
        ),
        Perception(
            id="perception-mismatch-root",
            actor_id="actor-1",
            source_id="world-1",
        ),
    )
    projected_state = projection.projected_state
    assert projected_state is not None

    strategy = Strategy(
        id="strategy-mismatch",
        actor_id="actor-1",
        root_node_id="node-root",
        nodes=[
            StrategyNode(
                node_id="node-root",
                action_id="action-root",  # different from projected_state.generating_action_id
                outcome_branches=[
                    StrategyOutcomeBranch(
                        branch_id="bad-branch",
                        projected_state=projected_state,  # generated by "action-other"
                    )
                ],
            )
        ],
    )

    with pytest.raises(ValueError, match="generated by the parent node action"):
        strategy.validate_tree()


def test_strategy_validate_tree_accepts_terminal_branch_with_projected_state():
    """A branch with projected_state but no child_node_id (terminal) is valid."""
    projection = DefaultProjectionTool().project_action(
        Action(
            id="action-terminal",
            actor_id="actor-1",
            world_id="world-1",
            space_id="space-1",
            action_type="move",
        ),
        Perception(
            id="perception-terminal-root",
            actor_id="actor-1",
            source_id="world-1",
        ),
    )
    projected_state = projection.projected_state
    assert projected_state is not None

    strategy = Strategy(
        id="strategy-terminal-branch",
        actor_id="actor-1",
        root_node_id="node-root",
        nodes=[
            StrategyNode(
                node_id="node-root",
                action_id="action-terminal",
                source_perception_id="perception-terminal-root",
                outcome_branches=[
                    StrategyOutcomeBranch(
                        branch_id="done",
                        label="success",
                        child_node_id=None,
                        projected_state=projected_state,
                    )
                ],
            )
        ],
    )

    strategy.validate_tree()  # must not raise


def test_build_branching_strategy_branches_carry_root_projected_state():
    """Each branch from the root node carries the root action's projected state."""
    strategy = build_branching_strategy(
        "strategy-branch-ps",
        Perception(
            id="perception-branch-ps-root",
            actor_id="actor-1",
            source_id="world-1",
        ),
        StrategyBuildStep(
            action=Action(
                id="action-root-ps",
                actor_id="actor-1",
                world_id="world-1",
                space_id="space-1",
                action_type="plan",
            ),
            children=[
                StrategyBuildStep(
                    action=Action(
                        id="action-child-a",
                        actor_id="actor-1",
                        world_id="world-1",
                        space_id="space-1",
                        action_type="explore",
                    ),
                    branch_label="option-a",
                ),
                StrategyBuildStep(
                    action=Action(
                        id="action-child-b",
                        actor_id="actor-1",
                        world_id="world-1",
                        space_id="space-1",
                        action_type="secure",
                    ),
                    branch_label="option-b",
                ),
            ],
        ),
    )

    root_node = strategy.get_node("node-0001-action-root-ps")
    assert root_node is not None
    assert len(root_node.outcome_branches) == 2
    for branch in root_node.outcome_branches:
        assert branch.projected_state is not None
        assert branch.projected_state.generating_action_id == "action-root-ps"


def test_build_linear_strategy_success_branch_carries_projected_state():
    """The success branch of each non-terminal node carries the projected state."""
    strategy = build_linear_strategy(
        "strategy-linear-ps",
        Perception(
            id="perception-linear-ps-root",
            actor_id="actor-1",
            source_id="world-1",
        ),
        [
            Action(
                id="action-step-1",
                actor_id="actor-1",
                world_id="world-1",
                space_id="space-1",
                action_type="move",
                state_changes={"context_updates": {"step": 1}},
            ),
            Action(
                id="action-step-2",
                actor_id="actor-1",
                world_id="world-1",
                space_id="space-1",
                action_type="observe",
                state_changes={"context_updates": {"step": 2}},
            ),
        ],
    )

    node1 = strategy.nodes[0]
    node2 = strategy.nodes[1]

    assert len(node1.outcome_branches) == 1
    branch = node1.outcome_branches[0]
    assert branch.projected_state is not None
    assert branch.projected_state.generating_action_id == "action-step-1"
    assert branch.projected_state.perception.id == node2.source_perception_id
    # terminal node has one terminal branch (no child, carries projected outcome)
    assert len(node2.outcome_branches) == 1
    terminal_branch = node2.outcome_branches[0]
    assert terminal_branch.child_node_id is None
    assert terminal_branch.projected_state is not None
    assert terminal_branch.projected_state.generating_action_id == "action-step-2"
