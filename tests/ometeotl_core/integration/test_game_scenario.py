"""Integration test: 2-actor game scenario end-to-end.

Exercises the complete game-layer chain:
  World + Actors + Perceptions + Strategies + Goals
    → GameState → NormalFormGame → BestResponseCalculator

Audit artifact written to local_lab/artifacts/generation/game_scenario.json.
"""

import json

import pytest

from tests.ometeotl_core._artifact_utils import write_json_artifact

from ometeotl_core.game.best_response import BestResponseCalculator
from ometeotl_core.game.game_state import GameState, PlayerProfile
from ometeotl_core.game.normal_form import IndependentPayoffFunction, NormalFormGame
from ometeotl_core.game.utility import LexicographicUtility, WeightedSumUtility
from ometeotl_core.model.actions import Action
from ometeotl_core.model.actors import Actor
from ometeotl_core.model.goals import Goal
from ometeotl_core.model.perception import Perception
from ometeotl_core.model.projection import ProjectedPerceptionState
from ometeotl_core.model.spaces import Space
from ometeotl_core.model.strategies import Strategy, StrategyNode, StrategyOutcomeBranch
from ometeotl_core.model.world import World


def _build_world() -> World:
    world = World(id="world-game-scenario")
    market = Space(id="space-market")
    world.add_space(market)
    return world


def _make_strategy(
    strategy_id: str,
    actor_id: str,
    *,
    gold: float,
    territory: float,
) -> Strategy:
    """Build a single-node terminal strategy with gold and territory metrics."""
    action = Action(
        id=f"action-{strategy_id}",
        actor_id=actor_id,
        world_id="world-game-scenario",
        space_id="space-market",
        action_type="move",
    )
    perception = Perception(
        id=f"p-{strategy_id}",
        actor_id=actor_id,
        source_id="world-game-scenario",
        context={"gold": gold, "territory": territory},
    )
    projected = ProjectedPerceptionState(
        source_perception_id=f"p-initial-{actor_id}",
        generating_action_id=action.id,
        perception=perception,
    )
    branch = StrategyOutcomeBranch(
        branch_id=f"{strategy_id}:terminal",
        label="outcome",
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


def _build_scenario() -> tuple[GameState, Actor, Actor]:
    """
    Two actors competing in a market.

    Actor-1 (merchant): values gold above all, uses WeightedSumUtility.
    Actor-2 (general):  values territory first, then gold (lexicographic).

    Strategies:
      merchant-trade → gold=6, territory=1   (good gold, low territory)
      merchant-raid  → gold=2, territory=4   (low gold, moderate territory)

      general-expand → gold=1, territory=8   (high territory, low gold)
      general-fortify→ gold=3, territory=5   (moderate both)
    """
    merchant = Actor(id="actor-merchant")
    general = Actor(id="actor-general")

    merchant_trade = _make_strategy(
        "merchant-trade", merchant.id, gold=6.0, territory=1.0
    )
    merchant_raid = _make_strategy(
        "merchant-raid", merchant.id, gold=2.0, territory=4.0
    )

    general_expand = _make_strategy(
        "general-expand", general.id, gold=1.0, territory=8.0
    )
    general_fortify = _make_strategy(
        "general-fortify", general.id, gold=3.0, territory=5.0
    )

    merchant_utility = WeightedSumUtility(
        framework_id="merchant-gold",
        metric_weights={"gold": 1.0, "territory": 0.2},
    )
    general_utility = LexicographicUtility(
        framework_id="general-expand",
        metric_order=["territory", "gold"],
    )

    merchant_goal = Goal(
        id="goal-merchant",
        actor_id=merchant.id,
        kind="final",
    )
    general_goal = Goal(
        id="goal-general",
        actor_id=general.id,
        kind="final",
    )

    merchant.add_goal(merchant_goal.id)
    general.add_goal(general_goal.id)

    p_merchant = PlayerProfile(
        actor=merchant,
        strategies=[merchant_trade, merchant_raid],
        utility_function=merchant_utility,
    )
    p_general = PlayerProfile(
        actor=general,
        strategies=[general_expand, general_fortify],
        utility_function=general_utility,
    )

    gs = GameState(
        id="gs-market-scenario",
        world_id="world-game-scenario",
        players=[p_merchant, p_general],
        metadata={"scenario": "market-competition"},
    )
    return gs, merchant, general


def test_normal_form_game_has_four_profiles():
    gs, _, _ = _build_scenario()
    game = NormalFormGame.from_game_state(
        gs, IndependentPayoffFunction(), game_id="game-market"
    )

    assert len(game.payoff_vectors) == 4


def test_merchant_best_response_is_trade():
    """Merchant prefers trade (gold=6) over raid (gold=2) regardless of general's move."""
    gs, merchant, general = _build_scenario()
    game = NormalFormGame.from_game_state(
        gs, IndependentPayoffFunction(), game_id="game-market"
    )
    calc = BestResponseCalculator()

    general_player = gs.player_for(general.id)
    assert general_player is not None

    for opp_strategy in general_player.strategies:
        result = calc.compute(merchant.id, {general.id: opp_strategy}, game)
        assert (
            result.best_strategy.id == "merchant-trade"
        ), f"Expected trade when general plays {opp_strategy.id}"


def test_general_best_response_is_expand():
    """General prefers expand (territory=8) over fortify (territory=5) regardless of merchant."""
    gs, merchant, general = _build_scenario()
    game = NormalFormGame.from_game_state(
        gs, IndependentPayoffFunction(), game_id="game-market"
    )
    calc = BestResponseCalculator()

    merchant_player = gs.player_for(merchant.id)
    assert merchant_player is not None

    for opp_strategy in merchant_player.strategies:
        result = calc.compute(general.id, {merchant.id: opp_strategy}, game)
        assert (
            result.best_strategy.id == "general-expand"
        ), f"Expected expand when merchant plays {opp_strategy.id}"


def test_audit_artifact_is_written():
    """Full chain produces a well-structured JSON audit artifact."""
    gs, merchant, general = _build_scenario()
    game = NormalFormGame.from_game_state(
        gs, IndependentPayoffFunction(), game_id="game-market"
    )
    calc = BestResponseCalculator()

    general_player = gs.player_for(general.id)
    merchant_player = gs.player_for(merchant.id)

    br_merchant = calc.compute(
        merchant.id, {general.id: general_player.strategies[0]}, game
    )
    br_general = calc.compute(
        general.id, {merchant.id: merchant_player.strategies[0]}, game
    )

    artifact = {
        "game": game.to_dict(),
        "best_response_merchant": br_merchant.to_dict(),
        "best_response_general": br_general.to_dict(),
    }

    path = write_json_artifact(
        layer="generation",
        name="game_scenario",
        payload=artifact,
    )

    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["game"]["id"] == "game-market"
    assert len(written["game"]["payoff_vectors"]) == 4
    assert written["best_response_merchant"]["best_strategy_id"] == "merchant-trade"
    assert written["best_response_general"]["best_strategy_id"] == "general-expand"
