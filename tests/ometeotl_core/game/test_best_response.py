"""Tests for ometeotl_core.game.best_response."""

import pytest

from ometeotl_core.game.best_response import BestResponseCalculator, BestResponseResult
from ometeotl_core.game.game_state import GameState, PlayerProfile
from ometeotl_core.game.normal_form import IndependentPayoffFunction, NormalFormGame
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


def _build_prisoner_dilemma_game() -> tuple[NormalFormGame, GameState]:
    """Classic prisoner's dilemma payoffs (row player perspective on gain)."""
    s_cooperate_a1 = _make_terminal_strategy("a1-cooperate", "actor-1", gain=3.0)
    s_defect_a1 = _make_terminal_strategy("a1-defect", "actor-1", gain=5.0)
    s_cooperate_a2 = _make_terminal_strategy("a2-cooperate", "actor-2", gain=3.0)
    s_defect_a2 = _make_terminal_strategy("a2-defect", "actor-2", gain=5.0)

    p1 = _make_player("actor-1", [s_cooperate_a1, s_defect_a1])
    p2 = _make_player("actor-2", [s_cooperate_a2, s_defect_a2])

    gs = GameState(id="gs-pd", world_id="world-1", players=[p1, p2])
    game = NormalFormGame.from_game_state(gs, IndependentPayoffFunction())
    return game, gs


class TestBestResponseCalculator:
    def test_returns_higher_gain_strategy(self):
        game, gs = _build_prisoner_dilemma_game()
        calc = BestResponseCalculator()

        opponent_profile = {"actor-2": gs.players[1].strategies[0]}
        result = calc.compute("actor-1", opponent_profile, game)

        # defect (gain=5) > cooperate (gain=3)
        assert result.best_strategy.id == "a1-defect"
        assert result.best_utility.value == pytest.approx(5.0)

    def test_all_responses_ordered_descending(self):
        game, gs = _build_prisoner_dilemma_game()
        calc = BestResponseCalculator()

        opponent_profile = {"actor-2": gs.players[1].strategies[0]}
        result = calc.compute("actor-1", opponent_profile, game)

        gains = [f.value for _, f in result.all_responses]
        assert gains == sorted(gains, reverse=True)

    def test_all_responses_includes_all_focal_strategies(self):
        game, gs = _build_prisoner_dilemma_game()
        calc = BestResponseCalculator()

        opponent_profile = {"actor-2": gs.players[1].strategies[0]}
        result = calc.compute("actor-1", opponent_profile, game)

        strategy_ids = {s.id for s, _ in result.all_responses}
        assert strategy_ids == {"a1-cooperate", "a1-defect"}

    def test_tie_breaking_is_deterministic_by_strategy_id(self):
        # Both strategies give the same gain → tie broken by strategy id
        s_tie_a = _make_terminal_strategy("a1-aaa", "actor-1", gain=2.0)
        s_tie_b = _make_terminal_strategy("a1-zzz", "actor-1", gain=2.0)
        s_opp = _make_terminal_strategy("a2-x", "actor-2", gain=1.0)

        p1 = _make_player("actor-1", [s_tie_b, s_tie_a])
        p2 = _make_player("actor-2", [s_opp])
        gs = GameState(id="gs-tie", world_id="world-1", players=[p1, p2])
        game = NormalFormGame.from_game_state(gs, IndependentPayoffFunction())

        calc = BestResponseCalculator()
        result = calc.compute("actor-1", {"actor-2": s_opp}, game)

        # Lexicographically smallest id wins on tie
        assert result.best_strategy.id == "a1-aaa"

    def test_raises_when_actor_not_in_game(self):
        game, _ = _build_prisoner_dilemma_game()
        calc = BestResponseCalculator()

        with pytest.raises(ValueError, match="not a player in this game"):
            calc.compute("ghost", {}, game)

    def test_raises_when_focal_actor_in_opponent_profile(self):
        game, gs = _build_prisoner_dilemma_game()
        calc = BestResponseCalculator()

        with pytest.raises(ValueError, match="must not contain the focal actor"):
            calc.compute(
                "actor-1",
                {"actor-1": gs.players[0].strategies[0]},
                game,
            )

    def test_raises_when_opponent_not_in_game(self):
        game, gs = _build_prisoner_dilemma_game()
        calc = BestResponseCalculator()

        ghost_strategy = _make_terminal_strategy("ghost-s", "ghost", gain=1.0)
        with pytest.raises(ValueError, match="not a player in this game"):
            calc.compute("actor-1", {"ghost": ghost_strategy}, game)

    def test_to_dict_structure(self):
        game, gs = _build_prisoner_dilemma_game()
        calc = BestResponseCalculator()

        opponent_profile = {"actor-2": gs.players[1].strategies[0]}
        result = calc.compute("actor-1", opponent_profile, game)
        d = result.to_dict()

        assert d["actor_id"] == "actor-1"
        assert "best_strategy_id" in d
        assert "best_utility" in d
        assert "all_responses" in d
        assert isinstance(d["all_responses"], list)
