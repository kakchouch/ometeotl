---
title: "PlayerProfile"
---

Source:
- [src/ometeotl_core/game/game_state.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/game/game_state.py)

Local role:
Binds one actor to their available strategies and utility function for a single game instance.

Big-picture role:
An actor in the world is not inherently a player — it becomes one when it holds a declared set of choices and a way to value outcomes. PlayerProfile is that declaration: it gives an actor a strategic identity by making explicit what it can do and what it is trying to achieve.

Inheritance:
- standard dataclass

Constructor:
- `PlayerProfile(actor, strategies, utility_function)`

Fields:
- `actor: Actor` — the actor participating as a player
- `strategies: list[Strategy]` — the set of admissible strategies for this player (at least one required)
- `utility_function: UtilityFunction` — the interpretive framework used to score this player's outcomes

Methods:
- `to_dict() -> JsonMap` — returns `actor_id` and `strategy_ids`

Important behavior:
- raises `ValueError` if `strategies` is empty

See also:
- [GameState](/ometeotl/documentation/class-reference/game/game-state/game-state/)
- [UtilityFunction](/ometeotl/documentation/class-reference/model/utility/utility-function/)
- [Strategy](/ometeotl/documentation/class-reference/model/strategies/strategy/)
