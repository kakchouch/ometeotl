"""Simple territory-control strategy game (CLI + web demo)."""

from .engine import (
    GameState,
    apply_player_action,
    check_victory,
    create_initial_state,
    legal_actions_for_player,
    serialize_state_for_ui,
    step_ai_turn,
)

__all__ = [
    "GameState",
    "apply_player_action",
    "check_victory",
    "create_initial_state",
    "legal_actions_for_player",
    "serialize_state_for_ui",
    "step_ai_turn",
]
