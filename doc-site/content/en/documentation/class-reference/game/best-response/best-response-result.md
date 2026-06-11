---
title: "BestResponseResult"
---

Source:
- [src/ometeotl_core/game/best_response.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/game/best_response.py)

Local role:
Result container for one best-response computation: the dominant strategy for a focal actor given a fixed opponent profile, plus a ranked list of all available responses.

Big-picture role:
Rational behavior in a competitive context is not "pick the best strategy in isolation" — it is "pick the best strategy given what others are doing." BestResponseResult is the answer to that conditional question: what is the optimal choice for this actor, and how do all other options compare, when opponents are assumed to play a specific way?

Inheritance:
- standard dataclass

Fields:
- `actor_id: str` — the focal player
- `opponent_profile: StrategyProfile` — the fixed opponent strategies used in this computation
- `best_strategy: Strategy` — the utility-maximising strategy
- `best_utility: UtilityFrame` — the utility frame for the best strategy
- `all_responses: list[tuple[Strategy, UtilityFrame]]` — all focal strategies ranked descending by utility, ties broken ascending by strategy id

Methods:
- `to_dict() -> JsonMap`

Example:

```python
calc = BestResponseCalculator()
result = calc.compute(
    actor_id="actor-1",
    opponent_profile={"actor-2": actor2_strategy},
    game=game,
)

print(result.actor_id)
print(result.best_strategy.id)
print(result.best_utility.scalar_value)

# Full ranking of all available responses, descending by utility
for strategy, frame in result.all_responses:
    print(strategy.id, frame.scalar_value)

data = result.to_dict()
```

See also:
- [BestResponseCalculator](/ometeotl/documentation/class-reference/game/best-response/best-response-calculator/)
- [NormalFormGame](/ometeotl/documentation/class-reference/game/normal-form/normal-form-game/)
