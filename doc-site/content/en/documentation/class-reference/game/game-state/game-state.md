---
title: "GameState"
---

Source:
- [src/ometeotl_core/game/game_state.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/game/game_state.py)

Local role:
Snapshot of the multi-actor game at a point in time, linking a world reference to the set of active players and their admissible strategies.

Big-picture role:
The world is continuous and ontologically rich; a game is a bounded, intentional framing of a situation. GameState is the act of framing — declaring who is playing, what choices they have, and what context their decisions are evaluated against. Everything outside this framing is irrelevant to the game.

Inheritance:
- standard dataclass

Constructor:
- `GameState(id, world_id, players, context={}, metadata={})`

Fields:
- `id: str` — unique game state identifier
- `world_id: str` — reference to the source World
- `players: list[PlayerProfile]` — all participating players (at least one; actor ids must be distinct)
- `context: JsonMap` — forwarded verbatim to utility evaluation (metric overrides, etc.)
- `metadata: JsonMap` — free-form annotations

Methods:
- `player_for(actor_id) -> PlayerProfile | None` — lookup by actor id
- `to_dict() -> JsonMap`

Important behavior:
- raises `ValueError` if `id` or `world_id` is empty
- raises `ValueError` if `players` is empty
- raises `ValueError` if any two players share the same `actor_id`

See also:
- [PlayerProfile](/ometeotl/documentation/class-reference/game/game-state/player-profile/)
- [NormalFormGame](/ometeotl/documentation/class-reference/game/normal-form/normal-form-game/)
