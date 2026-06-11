---
title: "IndependentPayoffFunction"
---

Source:
- [src/ometeotl_core/game/normal_form.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/game/normal_form.py)

Local role:
Concrete `PayoffFunction` where each player's utility depends only on their own strategy's terminal perception — no cross-actor projection.

Big-picture role:
Embodies the non-interference assumption: each actor's outcomes are determined solely by their own choices, regardless of what opponents do. This holds when actors compete over shared resources or space without one actor directly distorting another's perception — they coexist and compete, but do not manipulate each other's informational world.

Inheritance:
- `PayoffFunction`

Constructor:
- `IndependentPayoffFunction()` — stateless, no arguments

Methods:
- `evaluate(profile, players, context) -> dict[str, UtilityFrame]`
  - for each actor in `profile`, builds a `StrategyRanker` from the player's `utility_function` and calls `evaluate_strategy`
  - raises `ValueError` if the profile references an actor not present in `players`

Important behavior:
- player evaluation is completely independent; opponent strategies do not influence a player's terminal perception
- each call creates a new `StrategyRanker` per player (lightweight: holds only a reference)

See also:
- [PayoffFunction](/ometeotl/documentation/class-reference/game/normal-form/payoff-function/)
- [StrategyRanker](/ometeotl/documentation/class-reference/game/utility/strategy-ranker/)
- [NormalFormGame](/ometeotl/documentation/class-reference/game/normal-form/normal-form-game/)
