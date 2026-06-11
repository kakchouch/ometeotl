"""Local-only smoke tests for the examples strategy game engine."""

from examples.core_only_labs.strategy_game.engine import (
    PLAYER_BLUE,
    PLAYER_RED,
    apply_player_action,
    create_initial_state,
    legal_actions_for_player,
    serialize_state_for_ui,
    step_ai_turn,
)


def test_initial_state_has_two_players_and_claim_options() -> None:
    state = create_initial_state()
    payload = serialize_state_for_ui(state)

    assert payload["active_player"] == PLAYER_RED
    assert payload["scores"][PLAYER_RED] == 1
    assert payload["scores"][PLAYER_BLUE] == 1

    labels = [item["label"] for item in payload["legal_actions"]]
    assert "Move to B" in labels
    assert "Move to D" in labels


def test_move_then_ai_turn_progresses_state() -> None:
    state = create_initial_state()

    apply_player_action(state, action_type="move", target="B")
    assert state.active_player == PLAYER_BLUE

    chosen = step_ai_turn(state)

    assert chosen["action_type"] in {"move", "claim", "pass"}
    assert state.active_player == PLAYER_RED
    assert state.turn_number == 2


def test_illegal_human_action_is_rejected() -> None:
    state = create_initial_state()

    try:
        apply_player_action(state, action_type="move", target="F")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "Illegal action" in str(exc)


def test_ai_prefers_claiming_enemy_controlled_territory() -> None:
    state = create_initial_state()

    state.active_player = PLAYER_BLUE
    state.player_positions[PLAYER_BLUE] = "A"
    state.territory_owner["A"] = PLAYER_RED

    actions = legal_actions_for_player(state, PLAYER_BLUE)
    assert any(a["action_type"] == "claim" for a in actions)

    chosen = step_ai_turn(state)
    assert chosen["action_type"] == "claim"
    assert state.territory_owner["A"] == PLAYER_BLUE
