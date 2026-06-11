"""Best-response computation for normal-form games.

Given a NormalFormGame and a fixed opponent strategy profile, BestResponseCalculator
finds the strategy that maximises the focal actor's utility. Ranking uses the
rank_key tuple convention already established by StrategyRanker/RankedStrategy so
comparison semantics are identical across the game layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ometeotl_core.model.base import JsonMap
from ometeotl_core.model.strategies import Strategy
from ometeotl_core.model.utility import UtilityFrame

from .normal_form import NormalFormGame, StrategyProfile


@dataclass
class BestResponseResult:
    """Best-response for one actor given a fixed opponent strategy profile."""

    actor_id: str
    opponent_profile: StrategyProfile
    best_strategy: Strategy
    best_utility: UtilityFrame
    all_responses: list[tuple[Strategy, UtilityFrame]] = field(default_factory=list)

    def to_dict(self) -> JsonMap:
        return {
            "actor_id": self.actor_id,
            "opponent_profile": {aid: s.id for aid, s in self.opponent_profile.items()},
            "best_strategy_id": self.best_strategy.id,
            "best_utility": self.best_utility.to_dict(),
            "all_responses": [
                {"strategy_id": s.id, "utility": f.to_dict()}
                for s, f in self.all_responses
            ],
        }


class BestResponseCalculator:
    """Finds the best-response strategy for a focal actor against fixed opponents.

    Operates on a precomputed NormalFormGame so no re-evaluation is needed.
    Tie-breaking is deterministic: equal rank_keys are broken by strategy id
    (lexicographic), matching the convention in StrategyRanker.rank_strategies.
    """

    def compute(
        self,
        actor_id: str,
        opponent_profile: StrategyProfile,
        game: NormalFormGame,
    ) -> BestResponseResult:
        """Return the best-response for ``actor_id`` given fixed opponent strategies.

        Args:
            actor_id: The focal player whose best response is sought.
            opponent_profile: Fixed strategies for all other players (actor_id → Strategy).
            game: Precomputed NormalFormGame containing the full payoff matrix.

        Returns:
            BestResponseResult with the dominant strategy and a ranked list of all options.

        Raises:
            ValueError: If actor_id is not a player in the game, if opponent_profile
                references unknown actors, or if no matching payoff vectors are found.
        """
        player_ids = {p.actor.id for p in game.players}
        if actor_id not in player_ids:
            raise ValueError(f"Actor '{actor_id}' is not a player in this game")

        for opp_id in opponent_profile:
            if opp_id == actor_id:
                raise ValueError("opponent_profile must not contain the focal actor")
            if opp_id not in player_ids:
                raise ValueError(f"Opponent '{opp_id}' is not a player in this game")

        opponent_strategy_ids = {opp_id: s.id for opp_id, s in opponent_profile.items()}

        responses: list[tuple[Strategy, UtilityFrame]] = []
        for pv in game.payoff_vectors:
            profile_opponent_ids = {
                aid: s.id for aid, s in pv.profile.items() if aid != actor_id
            }
            if profile_opponent_ids != opponent_strategy_ids:
                continue

            focal_strategy = pv.profile.get(actor_id)
            focal_frame = pv.payoffs.get(actor_id)
            if focal_strategy is None or focal_frame is None:
                continue
            responses.append((focal_strategy, focal_frame))

        if not responses:
            raise ValueError(
                f"No payoff vectors found for actor '{actor_id}' with the given opponent profile"
            )

        def _numeric_key(frame: UtilityFrame) -> tuple[float, ...]:
            comparison = frame.metadata.get("comparison_values")
            if isinstance(comparison, list):
                return tuple(float(v) for v in comparison)
            if frame.is_multi_criteria:
                return tuple(float(v) for v in frame.value)  # type: ignore[arg-type]
            return (float(frame.scalar_value),)

        # Sort descending by utility, break ties ascending by strategy id.
        responses_sorted = sorted(
            responses,
            key=lambda item: (tuple(-v for v in _numeric_key(item[1])), item[0].id),
        )

        best_strategy, best_utility = responses_sorted[0]

        return BestResponseResult(
            actor_id=actor_id,
            opponent_profile=dict(opponent_profile),
            best_strategy=best_strategy,
            best_utility=best_utility,
            all_responses=list(responses_sorted),
        )
