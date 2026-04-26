"""Tests for ometeotl_core.game.utility."""

from ometeotl_core.game.utility import (
    LexicographicUtility,
    StrategyRanker,
    WeightedSumUtility,
)
from ometeotl_core.model.actions import Action
from ometeotl_core.model.actors import Actor
from ometeotl_core.model.perception import Perception
from ometeotl_core.model.projection import ProjectedPerceptionState
from ometeotl_core.model.strategies import (
    Strategy,
    StrategyNode,
    StrategyOutcomeBranch,
)


def _make_action(action_id: str) -> Action:
    return Action(
        id=action_id,
        actor_id="actor-1",
        world_id="world-1",
        space_id="space-1",
        action_type="test",
    )


def _make_perception(perception_id: str, **context):
    return Perception(
        id=perception_id,
        actor_id="actor-1",
        source_id="world-1",
        context=dict(context),
    )


def _make_projected_state(
    *,
    source_perception_id: str,
    generating_action_id: str,
    perception_id: str,
    **context,
) -> ProjectedPerceptionState:
    return ProjectedPerceptionState(
        source_perception_id=source_perception_id,
        generating_action_id=generating_action_id,
        perception=_make_perception(perception_id, **context),
    )


def test_weighted_sum_utility_returns_scalar_frame_with_metadata():
    utility = WeightedSumUtility(
        framework_id="material-gain",
        metric_weights={"wealth": 2.0, "risk": -1.5},
    )

    frame = utility.evaluate(
        perception=_make_perception("p-1", wealth=3.0, risk=1.0),
        actor=Actor(id="actor-1"),
        context={},
    )

    assert frame.value == 4.5
    assert frame.framework_id == "material-gain"
    assert frame.metadata["metric_values"] == {
        "risk": 1.0,
        "wealth": 3.0,
    }
    assert frame.metadata["metric_weights"] == {
        "risk": -1.5,
        "wealth": 2.0,
    }
    assert frame.metadata["weighted_components"] == {
        "risk": -1.5,
        "wealth": 6.0,
    }
    assert frame.metadata["comparison_values"] == [4.5]


def test_lexicographic_utility_uses_raw_values_and_directional_comparison():
    utility = LexicographicUtility(
        framework_id="survival-then-cost",
        metric_order=["safety", "cost"],
        metric_directions={"cost": "minimize"},
    )

    frame = utility.evaluate(
        perception=_make_perception(
            "p-2", safety=10.0, cost=2.0
        ),
        actor=Actor(id="actor-1"),
        context={},
    )

    assert frame.value == [10.0, 2.0]
    assert frame.criteria_labels == ["safety", "cost"]
    assert frame.metadata["criteria_directions"] == {
        "cost": "minimize",
        "safety": "maximize",
    }
    assert frame.metadata["comparison_values"] == [10.0, -2.0]


def test_strategy_ranker_orders_strategies_by_scalar_terminal_utility():
    actor = Actor(id="actor-1")
    utility = WeightedSumUtility("expected-gain", {"gain": 1.0})
    ranker = StrategyRanker(utility)

    action_a = _make_action("action-a")
    action_b = _make_action("action-b")

    strategy_a = Strategy(
        id="strategy-a",
        actor_id=actor.id,
        root_node_id="node-a",
        nodes=[
            StrategyNode(
                node_id="node-a",
                action_id=action_a.id,
                projected_state=_make_projected_state(
                    source_perception_id="p-source",
                    generating_action_id=action_a.id,
                    perception_id="p-a",
                    gain=1.0,
                ),
            )
        ],
    )
    strategy_b = Strategy(
        id="strategy-b",
        actor_id=actor.id,
        root_node_id="node-b",
        nodes=[
            StrategyNode(
                node_id="node-b",
                action_id=action_b.id,
                projected_state=_make_projected_state(
                    source_perception_id="p-source",
                    generating_action_id=action_b.id,
                    perception_id="p-b",
                    gain=3.0,
                ),
            )
        ],
    )

    ranked = ranker.rank_strategies(
        [strategy_a, strategy_b], actor=actor
    )

    assert [item.strategy.id for item in ranked] == [
        "strategy-b",
        "strategy-a",
    ]
    assert ranked[0].utility_frame.value == 3.0
    assert ranked[1].utility_frame.value == 1.0


def test_strategy_ranker_aggregates_branch_probabilities_over_terminal_nodes():
    actor = Actor(id="actor-1")
    utility = WeightedSumUtility("expected-gain", {"gain": 1.0})
    ranker = StrategyRanker(utility)

    root_action = _make_action("action-root")
    left_action = _make_action("action-left")
    right_action = _make_action("action-right")
    baseline_action = _make_action("action-baseline")

    root_state = _make_projected_state(
        source_perception_id="p-source",
        generating_action_id=root_action.id,
        perception_id="p-root-successor",
    )
    strategy_branching = Strategy(
        id="strategy-branching",
        actor_id=actor.id,
        root_node_id="root-node",
        nodes=[
            StrategyNode(
                node_id="root-node",
                action_id=root_action.id,
                projected_state=root_state,
                outcome_branches=[
                    StrategyOutcomeBranch(
                        branch_id="left",
                        child_node_id="left-node",
                        probability=0.25,
                    ),
                    StrategyOutcomeBranch(
                        branch_id="right",
                        child_node_id="right-node",
                        probability=0.75,
                    ),
                ],
            ),
            StrategyNode(
                node_id="left-node",
                action_id=left_action.id,
                source_perception_id=root_state.perception.id,
                projected_state=_make_projected_state(
                    source_perception_id=root_state.perception.id,
                    generating_action_id=left_action.id,
                    perception_id="p-left",
                    gain=4.0,
                ),
            ),
            StrategyNode(
                node_id="right-node",
                action_id=right_action.id,
                source_perception_id=root_state.perception.id,
                projected_state=_make_projected_state(
                    source_perception_id=root_state.perception.id,
                    generating_action_id=right_action.id,
                    perception_id="p-right",
                    gain=0.0,
                ),
            ),
        ],
    )
    strategy_baseline = Strategy(
        id="strategy-baseline",
        actor_id=actor.id,
        root_node_id="baseline-node",
        nodes=[
            StrategyNode(
                node_id="baseline-node",
                action_id=baseline_action.id,
                projected_state=_make_projected_state(
                    source_perception_id="p-source",
                    generating_action_id=baseline_action.id,
                    perception_id="p-baseline",
                    gain=0.5,
                ),
            )
        ],
    )

    ranked = ranker.rank_strategies(
        [strategy_baseline, strategy_branching],
        actor=actor,
    )

    assert [item.strategy.id for item in ranked] == [
        "strategy-branching",
        "strategy-baseline",
    ]
    assert ranked[0].utility_frame.value == 1.0
    assert ranked[0].terminal_probabilities == {
        "left-node": 0.25,
        "right-node": 0.75,
    }


def test_strategy_ranker_uses_lexicographic_rank_key_for_multi_criteria_frames():
    actor = Actor(id="actor-1")
    utility = LexicographicUtility(
        "survival-then-cost",
        ["safety", "cost"],
        metric_directions={"cost": "minimize"},
    )
    ranker = StrategyRanker(utility)

    action_a = _make_action("action-a")
    action_b = _make_action("action-b")

    safer_cheaper = Strategy(
        id="strategy-a",
        actor_id=actor.id,
        root_node_id="node-a",
        nodes=[
            StrategyNode(
                node_id="node-a",
                action_id=action_a.id,
                projected_state=_make_projected_state(
                    source_perception_id="p-source",
                    generating_action_id=action_a.id,
                    perception_id="p-a",
                    safety=10.0,
                    cost=5.0,
                ),
            )
        ],
    )
    safer_costlier = Strategy(
        id="strategy-b",
        actor_id=actor.id,
        root_node_id="node-b",
        nodes=[
            StrategyNode(
                node_id="node-b",
                action_id=action_b.id,
                projected_state=_make_projected_state(
                    source_perception_id="p-source",
                    generating_action_id=action_b.id,
                    perception_id="p-b",
                    safety=10.0,
                    cost=7.0,
                ),
            )
        ],
    )

    ranked = ranker.rank_strategies(
        [safer_costlier, safer_cheaper], actor=actor
    )

    assert [item.strategy.id for item in ranked] == [
        "strategy-a",
        "strategy-b",
    ]
    assert ranked[0].rank_key == (10.0, -5.0)
    assert ranked[1].rank_key == (10.0, -7.0)


def test_strategy_ranker_defaults_to_equal_weights_when_probabilities_missing():
    actor = Actor(id="actor-1")
    utility = WeightedSumUtility("expected-gain", {"gain": 1.0})
    ranker = StrategyRanker(utility)

    root_action = _make_action("action-root")
    left_action = _make_action("action-left")
    right_action = _make_action("action-right")

    root_state = _make_projected_state(
        source_perception_id="p-source",
        generating_action_id=root_action.id,
        perception_id="p-root-successor",
    )
    strategy = Strategy(
        id="strategy-equal",
        actor_id=actor.id,
        root_node_id="root-node",
        nodes=[
            StrategyNode(
                node_id="root-node",
                action_id=root_action.id,
                projected_state=root_state,
                outcome_branches=[
                    StrategyOutcomeBranch(
                        branch_id="left",
                        child_node_id="left-node",
                    ),
                    StrategyOutcomeBranch(
                        branch_id="right",
                        child_node_id="right-node",
                    ),
                ],
            ),
            StrategyNode(
                node_id="left-node",
                action_id=left_action.id,
                source_perception_id=root_state.perception.id,
                projected_state=_make_projected_state(
                    source_perception_id=root_state.perception.id,
                    generating_action_id=left_action.id,
                    perception_id="p-left",
                    gain=2.0,
                ),
            ),
            StrategyNode(
                node_id="right-node",
                action_id=right_action.id,
                source_perception_id=root_state.perception.id,
                projected_state=_make_projected_state(
                    source_perception_id=root_state.perception.id,
                    generating_action_id=right_action.id,
                    perception_id="p-right",
                    gain=0.0,
                ),
            ),
        ],
    )

    ranked_strategy = ranker.evaluate_strategy(
        strategy, actor=actor
    )

    assert ranked_strategy.utility_frame.value == 1.0
    assert ranked_strategy.terminal_probabilities == {
        "left-node": 0.5,
        "right-node": 0.5,
    }


def test_strategy_ranker_sums_duplicate_child_branch_probabilities():
    actor = Actor(id="actor-1")
    utility = WeightedSumUtility("expected-gain", {"gain": 1.0})
    ranker = StrategyRanker(utility)

    root_action = _make_action("action-root")
    left_action = _make_action("action-left")
    right_action = _make_action("action-right")

    root_state = _make_projected_state(
        source_perception_id="p-source",
        generating_action_id=root_action.id,
        perception_id="p-root-successor",
    )
    strategy = Strategy(
        id="strategy-duplicate-child",
        actor_id=actor.id,
        root_node_id="root-node",
        nodes=[
            StrategyNode(
                node_id="root-node",
                action_id=root_action.id,
                projected_state=root_state,
                outcome_branches=[
                    StrategyOutcomeBranch(
                        branch_id="left-a",
                        child_node_id="left-node",
                        probability=0.2,
                    ),
                    StrategyOutcomeBranch(
                        branch_id="left-b",
                        child_node_id="left-node",
                        probability=0.3,
                    ),
                    StrategyOutcomeBranch(
                        branch_id="right",
                        child_node_id="right-node",
                        probability=0.5,
                    ),
                ],
            ),
            StrategyNode(
                node_id="left-node",
                action_id=left_action.id,
                source_perception_id=root_state.perception.id,
                projected_state=_make_projected_state(
                    source_perception_id=root_state.perception.id,
                    generating_action_id=left_action.id,
                    perception_id="p-left",
                    gain=2.0,
                ),
            ),
            StrategyNode(
                node_id="right-node",
                action_id=right_action.id,
                source_perception_id=root_state.perception.id,
                projected_state=_make_projected_state(
                    source_perception_id=root_state.perception.id,
                    generating_action_id=right_action.id,
                    perception_id="p-right",
                    gain=0.0,
                ),
            ),
        ],
    )

    ranked_strategy = ranker.evaluate_strategy(
        strategy, actor=actor
    )

    assert ranked_strategy.terminal_probabilities == {
        "left-node": 0.5,
        "right-node": 0.5,
    }
    assert ranked_strategy.utility_frame.value == 1.0


def test_strategy_ranker_aggregates_duplicate_terminal_paths_in_dag():
    actor = Actor(id="actor-1")
    utility = WeightedSumUtility("expected-gain", {"gain": 1.0})
    ranker = StrategyRanker(utility)

    root_action = _make_action("action-root")
    left_action = _make_action("action-left")
    right_action = _make_action("action-right")
    terminal_action = _make_action("action-terminal")

    root_state = _make_projected_state(
        source_perception_id="p-source",
        generating_action_id=root_action.id,
        perception_id="p-root-successor",
    )
    shared_state = _make_projected_state(
        source_perception_id=root_state.perception.id,
        generating_action_id=left_action.id,
        perception_id="p-shared-successor",
    )

    strategy = Strategy(
        id="strategy-dag-duplicate-terminal",
        actor_id=actor.id,
        root_node_id="root-node",
        nodes=[
            StrategyNode(
                node_id="root-node",
                action_id=root_action.id,
                projected_state=root_state,
                outcome_branches=[
                    StrategyOutcomeBranch(
                        branch_id="to-left",
                        child_node_id="left-node",
                        probability=0.4,
                    ),
                    StrategyOutcomeBranch(
                        branch_id="to-right",
                        child_node_id="right-node",
                        probability=0.6,
                    ),
                ],
            ),
            StrategyNode(
                node_id="left-node",
                action_id=left_action.id,
                source_perception_id=root_state.perception.id,
                projected_state=shared_state,
                outcome_branches=[
                    StrategyOutcomeBranch(
                        branch_id="left-to-terminal",
                        child_node_id="terminal-node",
                        probability=1.0,
                    )
                ],
            ),
            StrategyNode(
                node_id="right-node",
                action_id=right_action.id,
                source_perception_id=root_state.perception.id,
                projected_state=_make_projected_state(
                    source_perception_id=root_state.perception.id,
                    generating_action_id=right_action.id,
                    perception_id="p-shared-successor",
                ),
                outcome_branches=[
                    StrategyOutcomeBranch(
                        branch_id="right-to-terminal",
                        child_node_id="terminal-node",
                        probability=1.0,
                    )
                ],
            ),
            StrategyNode(
                node_id="terminal-node",
                action_id=terminal_action.id,
                source_perception_id="p-shared-successor",
                projected_state=_make_projected_state(
                    source_perception_id="p-shared-successor",
                    generating_action_id=terminal_action.id,
                    perception_id="p-terminal",
                    gain=5.0,
                ),
            ),
        ],
    )

    ranked_strategy = ranker.evaluate_strategy(
        strategy, actor=actor
    )

    assert ranked_strategy.terminal_node_ids == ["terminal-node"]
    assert ranked_strategy.terminal_probabilities == {
        "terminal-node": 1.0
    }
    assert ranked_strategy.utility_frame.value == 5.0
