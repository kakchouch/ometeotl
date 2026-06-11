"""Multi-actor game state container.

Implements G-1 (actors → players) and G-3 (world state → game state) by
grouping PlayerProfiles into a snapshot that binds each actor to their
admissible strategies and utility function for a single game instance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ometeotl_core.model.actors import Actor
from ometeotl_core.model.base import (
    JsonMap,
    _canonical_json_map,
    _dict_from_data,
    _str_from_data,
)
from ometeotl_core.model.strategies import Strategy
from ometeotl_core.model.utility import UtilityFrame, UtilityFunction


@dataclass
class PlayerProfile:
    """Binds an actor to their available strategies and utility function for a game.

    Represents G-1 (actor → player) and G-2 (admissible actions → available strategies).
    """

    actor: Actor
    strategies: list[Strategy]
    utility_function: UtilityFunction

    def __post_init__(self) -> None:
        if not self.strategies:
            raise ValueError("PlayerProfile requires at least one strategy")

    def to_dict(self) -> JsonMap:
        return {
            "actor_id": self.actor.id,
            "strategy_ids": [s.id for s in self.strategies],
        }


@dataclass
class GameState:
    """Snapshot of the multi-actor game at a point in time (G-3).

    Links a world reference to the set of active players and their admissible
    strategies. ``context`` is forwarded to utility evaluation.
    """

    id: str
    world_id: str
    players: list[PlayerProfile]
    context: JsonMap = field(default_factory=dict)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("GameState id cannot be empty")
        if not self.world_id:
            raise ValueError("GameState world_id cannot be empty")
        if not self.players:
            raise ValueError("GameState requires at least one player")
        actor_ids = [p.actor.id for p in self.players]
        if len(actor_ids) != len(set(actor_ids)):
            raise ValueError("GameState players must have distinct actor ids")

    def player_for(self, actor_id: str) -> PlayerProfile | None:
        """Return the PlayerProfile for the given actor id, or None."""
        for player in self.players:
            if player.actor.id == actor_id:
                return player
        return None

    def to_dict(self) -> JsonMap:
        return {
            "id": self.id,
            "world_id": self.world_id,
            "players": [p.to_dict() for p in self.players],
            "context": _canonical_json_map(self.context),
            "metadata": _canonical_json_map(self.metadata),
        }
