---
title: "PayoffFunction"
---

Source:
- [src/ometeotl_core/game/normal_form.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/game/normal_form.py)

Local role:
Abstract base class defining how joint payoffs are derived from a strategy profile.

Big-picture role:
The relationship between strategies and outcomes is not fixed — it depends on how actors interact, whether their decisions influence each other's conditions, and what theory of interference is assumed. PayoffFunction is the expression of that theory: it answers the question "given that everyone plays these strategies, what does each player end up with?"

Inheritance:
- ABC

Abstract methods:
- `evaluate(profile, players, context) -> dict[str, UtilityFrame]`
  - `profile: StrategyProfile` — actor_id → Strategy for every player
  - `players: list[PlayerProfile]` — all participating players
  - `context: JsonMap` — forwarded from `GameState.context`
  - returns a `UtilityFrame` per player

See also:
- [IndependentPayoffFunction](/ometeotl/documentation/class-reference/game/normal-form/independent-payoff-function/)
- [NormalFormGame](/ometeotl/documentation/class-reference/game/normal-form/normal-form-game/)
