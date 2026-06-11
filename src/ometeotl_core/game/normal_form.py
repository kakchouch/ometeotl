"""Normal-form game representation.

Provides the payoff matrix abstraction over multi-actor strategy profiles
(G-7, G-8, G-9). A NormalFormGame is built from a GameState by enumerating
all combinations of players' strategies and evaluating each profile through a
PayoffFunction.

PayoffFunction is abstract; IndependentPayoffFunction is the V1 concrete
implementation where each player's utility depends only on their own strategy's
terminal perception — no cross-actor projection.
"""

from __future__ import annotations

import itertools
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from ometeotl_core.model.base import JsonMap, _canonical_json_map
from ometeotl_core.model.strategies import Strategy
from ometeotl_core.model.utility import UtilityFrame

from .game_state import GameState, PlayerProfile
from .utility import RankedStrategy, StrategyRanker

# actor_id → Strategy chosen for that actor in a single profile
StrategyProfile = dict[str, Strategy]


@dataclass
class PayoffVector:
    """One entry of the payoff matrix: a strategy profile and per-actor utility frames."""

    profile: StrategyProfile
    payoffs: dict[str, UtilityFrame]

    def to_dict(self) -> JsonMap:
        return {
            "profile": {actor_id: s.id for actor_id, s in self.profile.items()},
            "payoffs": {
                actor_id: frame.to_dict() for actor_id, frame in self.payoffs.items()
            },
        }


class PayoffFunction(ABC):
    """Abstract base class for joint payoff evaluation across a strategy profile.

    Subclasses define how each player's utility is derived from the combined
    strategy choices of all players. This abstraction keeps the door open for
    joint projection (where one actor's strategy affects another's terminal
    perception) without requiring it in V1.
    """

    @abstractmethod
    def evaluate(
        self,
        profile: StrategyProfile,
        players: list[PlayerProfile],
        context: JsonMap,
    ) -> dict[str, UtilityFrame]:
        """Return a utility frame for each player given the joint strategy profile.

        Args:
            profile: Mapping from actor_id to the Strategy chosen for this combination.
            players: All PlayerProfiles participating in the game.
            context: Forwarded evaluation context (metric overrides, etc.).

        Returns:
            Mapping from actor_id to UtilityFrame for each player in ``players``.
        """


class IndependentPayoffFunction(PayoffFunction):
    """Payoff function where each player's utility depends only on their own strategy.

    Each player's terminal perception is evaluated in isolation using their own
    UtilityFunction via StrategyRanker. No cross-actor projection is performed.
    This is the V1 default and sufficient for modelling competitive scenarios
    where actors do not directly alter each other's perception branches.
    """

    def evaluate(
        self,
        profile: StrategyProfile,
        players: list[PlayerProfile],
        context: JsonMap,
    ) -> dict[str, UtilityFrame]:
        payoffs: dict[str, UtilityFrame] = {}
        player_index = {p.actor.id: p for p in players}

        for actor_id, strategy in profile.items():
            player = player_index.get(actor_id)
            if player is None:
                raise ValueError(
                    f"Profile references actor '{actor_id}' not present in players"
                )
            ranker = StrategyRanker(player.utility_function)
            ranked: RankedStrategy = ranker.evaluate_strategy(
                strategy, actor=player.actor, context=context
            )
            payoffs[actor_id] = ranked.utility_frame

        return payoffs


@dataclass
class NormalFormGame:
    """Full payoff matrix for a multi-actor game.

    Built from a GameState by enumerating all combinations of player strategies
    and evaluating each via a PayoffFunction. Scalability is O(∏ strategy counts)
    — intentionally small-game scoped for V1.
    """

    id: str
    players: list[PlayerProfile]
    payoff_vectors: list[PayoffVector]

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("NormalFormGame id cannot be empty")
        if not self.players:
            raise ValueError("NormalFormGame requires at least one player")

    @classmethod
    def from_game_state(
        cls,
        game_state: GameState,
        payoff_function: PayoffFunction,
        *,
        game_id: Optional[str] = None,
    ) -> NormalFormGame:
        """Build the full payoff matrix from a GameState.

        Enumerates the Cartesian product of each player's strategy list and
        evaluates every combination through ``payoff_function``.
        """
        player_ids = [p.actor.id for p in game_state.players]
        strategy_lists = [p.strategies for p in game_state.players]

        payoff_vectors: list[PayoffVector] = []
        for combo in itertools.product(*strategy_lists):
            profile: StrategyProfile = {
                actor_id: strategy for actor_id, strategy in zip(player_ids, combo)
            }
            payoffs = payoff_function.evaluate(
                profile, game_state.players, game_state.context
            )
            payoff_vectors.append(PayoffVector(profile=profile, payoffs=payoffs))

        return cls(
            id=game_id or str(uuid.uuid4()),
            players=game_state.players,
            payoff_vectors=payoff_vectors,
        )

    def payoffs_for_profile(self, profile: StrategyProfile) -> Optional[PayoffVector]:
        """Return the PayoffVector matching the given strategy profile, or None."""
        target = {actor_id: s.id for actor_id, s in profile.items()}
        for pv in self.payoff_vectors:
            candidate = {actor_id: s.id for actor_id, s in pv.profile.items()}
            if candidate == target:
                return pv
        return None

    def to_dict(self) -> JsonMap:
        return {
            "id": self.id,
            "player_ids": [p.actor.id for p in self.players],
            "payoff_vectors": [pv.to_dict() for pv in self.payoff_vectors],
        }
