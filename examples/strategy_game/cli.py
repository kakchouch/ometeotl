"""CLI runner for the examples strategy game."""

from __future__ import annotations

from examples.strategy_game.engine import (
    PLAYER_BLUE,
    PLAYER_RED,
    apply_player_action,
    create_initial_state,
    serialize_state_for_ui,
    step_ai_turn,
)


def _print_state(payload: dict[str, object]) -> None:
    scores = payload["scores"]
    print("\n=== Territory Control ===")
    print(f"Turn: {payload['turn_number']} | Active: {payload['active_player']}")
    print(f"Score - Red: {scores[PLAYER_RED]} | Blue: {scores[PLAYER_BLUE]}")
    print("Board:")

    for territory in payload["territories"]:
        marker = []
        if territory["red_here"] == "1":
            marker.append("R")
        if territory["blue_here"] == "1":
            marker.append("B")
        icon = "/".join(marker) if marker else "-"
        owner = territory["owner"] or "none"
        print(f"  {territory['id']}: owner={owner}, units={icon}")

    print("Recent actions:")
    for line in payload["action_log"]:
        print(f"  - {line}")


def run_cli_game() -> None:
    state = create_initial_state()

    while not state.game_over:
        payload = serialize_state_for_ui(state)
        _print_state(payload)

        actions = payload["legal_actions"]
        print("\nChoose action:")
        for idx, action in enumerate(actions, start=1):
            print(f"  {idx}. {action['label']}")

        try:
            choice = int(input("Action number: ").strip())
            picked = actions[choice - 1]
        except (ValueError, IndexError):
            print("Invalid choice, try again.")
            continue

        try:
            apply_player_action(
                state,
                action_type=picked["action_type"],
                target=picked["target"],
            )
        except ValueError as exc:
            print(f"Action rejected: {exc}")
            continue

        if state.game_over:
            break

        ai_action = step_ai_turn(state)
        print(f"AI played: {ai_action['label']}")

    final_payload = serialize_state_for_ui(state)
    _print_state(final_payload)
    if state.winner == "draw":
        print("\nGame over: draw")
    else:
        winner = "Red" if state.winner == PLAYER_RED else "Blue"
        print(f"\nGame over: {winner} wins")


if __name__ == "__main__":
    run_cli_game()
