---
title: "NormalFormGame"
---

Source:
- [src/ometeotl_core/game/normal_form.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/game/normal_form.py)

Local role:
Full payoff matrix for a multi-actor game: all strategy profile combinations and their per-player utility outcomes.

Big-picture role:
Competition is not just a property of individual intentions — it emerges from the structure of choices available to all participants simultaneously. NormalFormGame captures that structure: the complete map of what every combination of decisions produces for every player. It makes rivalry and cooperation visible as patterns in outcomes, not as declared relationships between actors.

Inheritance:
- standard dataclass

Constructor:
- `NormalFormGame(id, players, payoff_vectors)`
- raises `ValueError` if `id` is empty, `players` is empty, or two players share the same `actor_id`

Class methods:
- `from_game_state(game_state, payoff_function, *, game_id=None) -> NormalFormGame`
  - enumerates the Cartesian product of all players' strategy lists
  - evaluates each combination through `payoff_function`
  - complexity: O(∏ strategy counts) — intentionally bounded for V1 small-game scope

Fields:
- `id: str`
- `players: list[PlayerProfile]`
- `payoff_vectors: list[PayoffVector]` — one entry per strategy profile combination

Methods:
- `payoffs_for_profile(profile) -> PayoffVector | None` — lookup by strategy ids; returns `None` if not found
- `to_dict() -> JsonMap`

Example:

```python
from ometeotl_core.game.normal_form import NormalFormGame, IndependentPayoffFunction

# Build the full payoff matrix from a game state
payoff_fn = IndependentPayoffFunction()
game = NormalFormGame.from_game_state(game_state, payoff_fn)

# Look up payoffs for a specific strategy combination
profile = {pp.actor.id: pp.strategies[0] for pp in game_state.players}
vector = game.payoffs_for_profile(profile)
if vector:
    for actor_id, frame in vector.payoffs.items():
        print(actor_id, frame.scalar_value)
```

See also:
- [GameState](/ometeotl/documentation/class-reference/game/game-state/game-state/)
- [PayoffVector](/ometeotl/documentation/class-reference/game/normal-form/payoff-vector/)
- [PayoffFunction](/ometeotl/documentation/class-reference/game/normal-form/payoff-function/)
- [BestResponseCalculator](/ometeotl/documentation/class-reference/game/best-response/best-response-calculator/)
