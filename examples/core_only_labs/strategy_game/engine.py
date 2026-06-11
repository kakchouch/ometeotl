"""Shared deterministic engine for a minimal territory-control game.

This module intentionally lives in examples so core architecture remains
teleologically neutral while still demonstrating a playable end-to-end flow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict

from ometeotl_core.model.actors import Actor
from ometeotl_core.model.spaces import Space
from ometeotl_core.model.world import World

PLAYER_RED = "player-red"
PLAYER_BLUE = "player-blue"


class GameAction(TypedDict):
    """A single legal action for the current player."""

    action_type: str
    target: str
    label: str


@dataclass
class GameState:
    """Runtime state for the examples strategy game."""

    world: World
    adjacency: dict[str, list[str]]
    territory_owner: dict[str, str]
    player_positions: dict[str, str]
    turn_number: int = 1
    active_player: str = PLAYER_RED
    max_turns: int = 12
    winner: str = ""
    game_over: bool = False
    action_log: list[str] = field(default_factory=list)


def _build_world() -> World:
    world = World(id="local-lab-strategy-world")
    for territory in ["A", "B", "C", "D", "E", "F"]:
        space = Space(id=f"territory-{territory}")
        space.label = f"Territory {territory}"
        world.add_space(space)

    red = Actor(id=PLAYER_RED)
    blue = Actor(id=PLAYER_BLUE)
    red.label = "Red Commander"
    blue.label = "Blue Strategist"
    world.register_object(red)
    world.register_object(blue)
    world.place_object(red.id, "territory-A")
    world.place_object(blue.id, "territory-F")
    return world


def create_initial_state() -> GameState:
    """Initialize a deterministic two-player territory-control state."""

    adjacency = {
        "A": ["B", "D"],
        "B": ["A", "C", "E"],
        "C": ["B", "F"],
        "D": ["A", "E"],
        "E": ["B", "D", "F"],
        "F": ["C", "E"],
    }

    state = GameState(
        world=_build_world(),
        adjacency=adjacency,
        territory_owner={"A": PLAYER_RED, "F": PLAYER_BLUE},
        player_positions={PLAYER_RED: "A", PLAYER_BLUE: "F"},
        action_log=["Game initialized: Red controls A, Blue controls F."],
    )
    return state


def _score(state: GameState, player_id: str) -> int:
    return sum(1 for owner in state.territory_owner.values() if owner == player_id)


def legal_actions_for_player(state: GameState, player_id: str) -> list[GameAction]:
    """List legal actions for one player in the current state."""

    if state.game_over:
        return []

    current = state.player_positions[player_id]
    actions: list[GameAction] = []

    if state.territory_owner.get(current) != player_id:
        actions.append(
            {
                "action_type": "claim",
                "target": current,
                "label": f"Claim territory {current}",
            }
        )

    for target in sorted(state.adjacency[current]):
        actions.append(
            {
                "action_type": "move",
                "target": target,
                "label": f"Move to {target}",
            }
        )

    actions.append({"action_type": "pass", "target": "", "label": "Pass turn"})
    return actions


def _next_player(player_id: str) -> str:
    return PLAYER_BLUE if player_id == PLAYER_RED else PLAYER_RED


def _record_and_finalize_turn(state: GameState, message: str) -> None:
    state.action_log.append(message)
    if state.active_player == PLAYER_BLUE:
        state.turn_number += 1
    state.active_player = _next_player(state.active_player)


def check_victory(state: GameState) -> str:
    """Return winner id when game ends, otherwise empty string."""

    red_score = _score(state, PLAYER_RED)
    blue_score = _score(state, PLAYER_BLUE)

    if red_score >= 4:
        return PLAYER_RED
    if blue_score >= 4:
        return PLAYER_BLUE
    if state.turn_number > state.max_turns:
        if red_score > blue_score:
            return PLAYER_RED
        if blue_score > red_score:
            return PLAYER_BLUE
        return "draw"
    return ""


def _apply_action(
    state: GameState, player_id: str, action_type: str, target: str
) -> None:
    if action_type == "claim":
        current = state.player_positions[player_id]
        if target != current:
            raise ValueError("Claim target must be the current territory")
        state.territory_owner[current] = player_id
        _record_and_finalize_turn(state, f"{player_id} claimed territory {current}.")
        return

    if action_type == "move":
        current = state.player_positions[player_id]
        if target not in state.adjacency[current]:
            raise ValueError("Move target is not adjacent")
        state.player_positions[player_id] = target
        _record_and_finalize_turn(
            state, f"{player_id} moved from {current} to {target}."
        )
        return

    if action_type == "pass":
        _record_and_finalize_turn(state, f"{player_id} passed.")
        return

    raise ValueError(f"Unsupported action type: {action_type}")


def apply_player_action(state: GameState, action_type: str, target: str = "") -> None:
    """Apply one action for the active player after legal-action validation."""

    if state.game_over:
        raise ValueError("Game is already over")
    if state.active_player != PLAYER_RED:
        raise ValueError("It is not the human player's turn")

    legal = {
        (item["action_type"], item["target"])
        for item in legal_actions_for_player(state, PLAYER_RED)
    }
    key = (action_type, target)
    if key not in legal:
        raise ValueError("Illegal action for current state")

    _apply_action(state, PLAYER_RED, action_type, target)
    winner = check_victory(state)
    if winner:
        state.winner = winner
        state.game_over = True


def _ai_action_score(state: GameState, action: GameAction) -> tuple[int, str, str]:
    action_type = action["action_type"]
    target = action["target"]
    current = state.player_positions[PLAYER_BLUE]

    if action_type == "claim":
        owner = state.territory_owner.get(current)
        if owner == PLAYER_RED:
            return (5, action_type, target)
        return (4, action_type, target)

    if action_type == "move":
        owner = state.territory_owner.get(target)
        if owner == PLAYER_RED:
            return (3, action_type, target)
        if owner is None:
            return (2, action_type, target)
        return (1, action_type, target)

    return (0, action_type, target)


def step_ai_turn(state: GameState) -> GameAction:
    """Play deterministic AI turn for blue player and return chosen action."""

    if state.game_over:
        raise ValueError("Game is already over")
    if state.active_player != PLAYER_BLUE:
        raise ValueError("It is not the AI player's turn")

    actions = legal_actions_for_player(state, PLAYER_BLUE)
    chosen = sorted(
        actions, key=lambda item: _ai_action_score(state, item), reverse=True
    )[0]
    _apply_action(state, PLAYER_BLUE, chosen["action_type"], chosen["target"])

    winner = check_victory(state)
    if winner:
        state.winner = winner
        state.game_over = True

    return chosen


def serialize_state_for_ui(state: GameState) -> dict[str, object]:
    """Serialize runtime state for CLI/web rendering."""

    red_score = _score(state, PLAYER_RED)
    blue_score = _score(state, PLAYER_BLUE)

    territories: list[dict[str, str]] = []
    for territory in sorted(state.adjacency.keys()):
        territories.append(
            {
                "id": territory,
                "owner": state.territory_owner.get(territory, ""),
                "red_here": (
                    "1" if state.player_positions[PLAYER_RED] == territory else "0"
                ),
                "blue_here": (
                    "1" if state.player_positions[PLAYER_BLUE] == territory else "0"
                ),
            }
        )

    return {
        "turn_number": state.turn_number,
        "active_player": state.active_player,
        "game_over": state.game_over,
        "winner": state.winner,
        "scores": {PLAYER_RED: red_score, PLAYER_BLUE: blue_score},
        "territories": territories,
        "legal_actions": legal_actions_for_player(state, state.active_player),
        "action_log": list(state.action_log[-12:]),
    }
