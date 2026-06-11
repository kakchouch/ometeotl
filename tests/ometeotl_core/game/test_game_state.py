"""Tests for ometeotl_core.game.game_state."""

import pytest

from ometeotl_core.game.game_state import GameState, PlayerProfile
from ometeotl_core.game.utility import WeightedSumUtility
from ometeotl_core.model.actions import Action
from ometeotl_core.model.actors import Actor
from ometeotl_core.model.perception import Perception
from ometeotl_core.model.projection import ProjectedPerceptionState
from ometeotl_core.model.strategies import Strategy, StrategyNode, StrategyOutcomeBranch


def _make_actor(actor_id: str) -> Actor:
    return Actor(id=actor_id)


def _make_terminal_strategy(strategy_id: str, actor_id: str, gain: float) -> Strategy:
    action = Action(
        id=f"action-{strategy_id}",
        actor_id=actor_id,
        world_id="world-1",
        space_id="space-1",
        action_type="test",
    )
    perception = Perception(
        id=f"p-{strategy_id}",
        actor_id=actor_id,
        source_id="world-1",
        context={"gain": gain},
    )
    projected = ProjectedPerceptionState(
        source_perception_id="p-source",
        generating_action_id=action.id,
        perception=perception,
    )
    branch = StrategyOutcomeBranch(
        branch_id=f"{strategy_id}:terminal",
        label="terminal",
        child_node_id=None,
        projected_state=projected,
    )
    node = StrategyNode(
        node_id=f"node-{strategy_id}",
        action_id=action.id,
        outcome_branches=[branch],
    )
    return Strategy(
        id=strategy_id,
        actor_id=actor_id,
        root_node_id=node.node_id,
        nodes=[node],
    )


def _make_utility(framework_id: str) -> WeightedSumUtility:
    return WeightedSumUtility(framework_id=framework_id, metric_weights={"gain": 1.0})


class TestPlayerProfile:
    def test_basic_construction(self):
        actor = _make_actor("actor-1")
        strategy = _make_terminal_strategy("s1", "actor-1", gain=1.0)
        utility = _make_utility("fw-1")

        profile = PlayerProfile(
            actor=actor, strategies=[strategy], utility_function=utility
        )

        assert profile.actor.id == "actor-1"
        assert len(profile.strategies) == 1
        assert profile.utility_function is utility

    def test_requires_at_least_one_strategy(self):
        actor = _make_actor("actor-1")
        utility = _make_utility("fw-1")

        with pytest.raises(ValueError, match="at least one strategy"):
            PlayerProfile(actor=actor, strategies=[], utility_function=utility)

    def test_to_dict_contains_actor_id_and_strategy_ids(self):
        actor = _make_actor("actor-1")
        s1 = _make_terminal_strategy("s1", "actor-1", gain=1.0)
        s2 = _make_terminal_strategy("s2", "actor-1", gain=2.0)
        utility = _make_utility("fw-1")

        profile = PlayerProfile(
            actor=actor, strategies=[s1, s2], utility_function=utility
        )
        d = profile.to_dict()

        assert d["actor_id"] == "actor-1"
        assert set(d["strategy_ids"]) == {"s1", "s2"}


class TestGameState:
    def _make_profile(self, actor_id: str) -> PlayerProfile:
        actor = _make_actor(actor_id)
        strategy = _make_terminal_strategy(f"s-{actor_id}", actor_id, gain=1.0)
        utility = _make_utility(f"fw-{actor_id}")
        return PlayerProfile(
            actor=actor, strategies=[strategy], utility_function=utility
        )

    def test_basic_construction(self):
        p1 = self._make_profile("actor-1")
        p2 = self._make_profile("actor-2")
        gs = GameState(id="gs-1", world_id="world-1", players=[p1, p2])

        assert gs.id == "gs-1"
        assert gs.world_id == "world-1"
        assert len(gs.players) == 2

    def test_requires_non_empty_id(self):
        p1 = self._make_profile("actor-1")
        with pytest.raises(ValueError, match="id cannot be empty"):
            GameState(id="", world_id="world-1", players=[p1])

    def test_requires_non_empty_world_id(self):
        p1 = self._make_profile("actor-1")
        with pytest.raises(ValueError, match="world_id cannot be empty"):
            GameState(id="gs-1", world_id="", players=[p1])

    def test_requires_at_least_one_player(self):
        with pytest.raises(ValueError, match="at least one player"):
            GameState(id="gs-1", world_id="world-1", players=[])

    def test_rejects_duplicate_actor_ids(self):
        p1 = self._make_profile("actor-1")
        p1_dup = self._make_profile("actor-1")
        with pytest.raises(ValueError, match="distinct actor ids"):
            GameState(id="gs-1", world_id="world-1", players=[p1, p1_dup])

    def test_player_for_returns_correct_profile(self):
        p1 = self._make_profile("actor-1")
        p2 = self._make_profile("actor-2")
        gs = GameState(id="gs-1", world_id="world-1", players=[p1, p2])

        assert gs.player_for("actor-1") is p1
        assert gs.player_for("actor-2") is p2
        assert gs.player_for("unknown") is None

    def test_to_dict_structure(self):
        p1 = self._make_profile("actor-1")
        p2 = self._make_profile("actor-2")
        gs = GameState(
            id="gs-1",
            world_id="world-1",
            players=[p1, p2],
            context={"round": 1},
            metadata={"note": "test"},
        )
        d = gs.to_dict()

        assert d["id"] == "gs-1"
        assert d["world_id"] == "world-1"
        assert len(d["players"]) == 2
        assert d["context"] == {"round": 1}
        assert d["metadata"] == {"note": "test"}
