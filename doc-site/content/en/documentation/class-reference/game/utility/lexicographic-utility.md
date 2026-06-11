---
title: "LexicographicUtility"
---

Source:
- [src/ometeotl_core/game/utility.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/game/utility.py)

Local role:
Vector-valued utility combinator with explicit criterion ordering and direction.

Big-picture role:
Game-layer multi-criteria scoring primitive for lexicographic ranking.

Inheritance:
- [UtilityFunction](/ometeotl/documentation/class-reference/model/utility/utility-function/)

Constructor:
- `LexicographicUtility(framework_id, metric_order, metric_directions=None)`

Method:
- `evaluate(perception, actor, context) -> UtilityFrame`

Example:

```python
from ometeotl_core.game.utility import LexicographicUtility

# Safety is paramount; speed is the tiebreaker
utility = LexicographicUtility(
    framework_id="safety_first",
    metric_order=["safety", "speed"],
    metric_directions={"safety": "max", "speed": "max"},
)
frame = utility.evaluate(
    perception,
    actor,
    context={"safety": 0.9, "speed": 0.5},
)
print(frame.value)            # [0.9, 0.5]
print(frame.criteria_labels)  # ["safety", "speed"]
print(frame.is_multi_criteria) # True
```

See also:
- [WeightedSumUtility](/ometeotl/documentation/class-reference/game/utility/weighted-sum-utility/)
- [StrategyRanker](/ometeotl/documentation/class-reference/game/utility/strategy-ranker/)