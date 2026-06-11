"""Tests for ometeotl_core.game.normal_form."""

import pytest

from ometeotl_core.game.game_state import GameState, PlayerProfile
from ometeotl_core.game.normal_form import (
    IndependentPayoffFunction,
    NormalFormGame,
    PayoffVector,
)
from ometeotl_core.game.utility import WeightedSumUtility
from ometeotl_core.model.actions import Action
from ometeotl_core.model.actors import Actor
from ometeotl_core.model.perception import Perception
from ometeotl_core.model.projection import ProjectedPerceptionState
from ometeotl_core.model.strategies import Strategy, StrategyNode, StrategyOutcomeBranch


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


def _make_player(actor_id: str, strategies: list[Strategy]) -> PlayerProfile:
    actor = Actor(id=actor_id)
    utility = WeightedSumUtility(
        framework_id=f"fw-{actor_id}", metric_weights={"gain": 1.0}
    )
    return PlayerProfile(actor=actor, strategies=strategies, utility_function=utility)


def _make_two_player_game_state() -> GameState:
    """2 players × 2 strategies each → 4 payoff profiles."""
    p1 = _make_player(
        "actor-1",
        [
            _make_terminal_strategy("a1-cooperate", "actor-1", gain=3.0),
            _make_terminal_strategy("a1-defect", "actor-1", gain=5.0),
        ],
    )
    p2 = _make_player(
        "actor-2",
        [
            _make_terminal_strategy("a2-cooperate", "actor-2", gain=3.0),
            _make_terminal_strategy("a2-defect", "actor-2", gain=5.0),
        ],
    )
    return GameState(id="gs-1", world_id="world-1", players=[p1, p2])


class TestIndependentPayoffFunction:
    def test_evaluates_each_player_independently(self):
        gs = _make_two_player_game_state()
        fn = IndependentPayoffFunction()

        profile = {
            "actor-1": gs.players[0].strategies[0],
            "actor-2": gs.players[1].strategies[1],
        }
        payoffs = fn.evaluate(profile, gs.players, {})

        assert set(payoffs.keys()) == {"actor-1", "actor-2"}
        assert payoffs["actor-1"].value == pytest.approx(3.0)
        assert payoffs["actor-2"].value == pytest.approx(5.0)

    def test_raises_for_unknown_actor_in_profile(self):
        gs = _make_two_player_game_state()
        fn = IndependentPayoffFunction()

        bad_strategy = _make_terminal_strategy("ghost-s", "ghost", gain=1.0)
        profile = {
            "actor-1": gs.players[0].strategies[0],
            "ghost": bad_strategy,
        }
        with pytest.raises(ValueError, match="not present in players"):
            fn.evaluate(profile, gs.players, {})


class TestNormalFormGame:
    def test_from_game_state_produces_correct_number_of_vectors(self):
        gs = _make_two_player_game_state()
        game = NormalFormGame.from_game_state(gs, IndependentPayoffFunction())

        # 2 players × 2 strategies = 4 profiles
        assert len(game.payoff_vectors) == 4

    def test_from_game_state_single_player(self):
        p1 = _make_player(
            "actor-1",
            [
                _make_terminal_strategy("s1", "actor-1", gain=1.0),
                _make_terminal_strategy("s2", "actor-1", gain=2.0),
            ],
        )
        gs = GameState(id="gs-solo", world_id="world-1", players=[p1])
        game = NormalFormGame.from_game_state(gs, IndependentPayoffFunction())

        assert len(game.payoff_vectors) == 2

    def test_payoffs_for_profile_returns_correct_vector(self):
        gs = _make_two_player_game_state()
        game = NormalFormGame.from_game_state(gs, IndependentPayoffFunction())

        target_profile = {
            "actor-1": gs.players[0].strategies[0],
            "actor-2": gs.players[1].strategies[1],
        }
        pv = game.payoffs_for_profile(target_profile)

        assert pv is not None
        assert pv.payoffs["actor-1"].value == pytest.approx(3.0)
        assert pv.payoffs["actor-2"].value == pytest.approx(5.0)

    def test_payoffs_for_profile_returns_none_for_unknown_profile(self):
        gs = _make_two_player_game_state()
        game = NormalFormGame.from_game_state(gs, IndependentPayoffFunction())

        ghost_strategy = _make_terminal_strategy("ghost", "actor-1", gain=99.0)
        missing_profile = {
            "actor-1": ghost_strategy,
            "actor-2": gs.players[1].strategies[0],
        }
        assert game.payoffs_for_profile(missing_profile) is None

    def test_all_payoff_vectors_have_both_player_payoffs(self):
        gs = _make_two_player_game_state()
        game = NormalFormGame.from_game_state(gs, IndependentPayoffFunction())

        for pv in game.payoff_vectors:
            assert "actor-1" in pv.payoffs
            assert "actor-2" in pv.payoffs

    def test_to_dict_structure(self):
        gs = _make_two_player_game_state()
        game = NormalFormGame.from_game_state(
            gs, IndependentPayoffFunction(), game_id="game-test"
        )
        d = game.to_dict()

        assert d["id"] == "game-test"
        assert set(d["player_ids"]) == {"actor-1", "actor-2"}
        assert len(d["payoff_vectors"]) == 4

    def test_rejects_empty_id(self):
        gs = _make_two_player_game_state()
        game = NormalFormGame.from_game_state(gs, IndependentPayoffFunction())

    def test_rejects_duplicate_player_ids(self):
        gs = _make_two_player_game_state()
        game = NormalFormGame.from_game_state(gs, IndependentPayoffFunction())
        dup_players = [game.players[0], game.players[0]]

        with pytest.raises(ValueError, match="distinct actor ids"):
            NormalFormGame(
                id="game-dup", players=dup_players, payoff_vectors=game.payoff_vectors
            )

        with pytest.raises(ValueError, match="id cannot be empty"):
            NormalFormGame(
                id="", players=game.players, payoff_vectors=game.payoff_vectors
            )
