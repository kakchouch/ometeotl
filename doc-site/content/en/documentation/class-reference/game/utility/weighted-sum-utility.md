---
title: "WeightedSumUtility"
---

Source:
- [src/ometeotl_core/game/utility.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/game/utility.py)

Local role:
Scalar utility combinator that computes weighted linear sums over metrics.

Big-picture role:
Default game-layer scalar scoring primitive used by [StrategyRanker](/ometeotl/documentation/class-reference/game/utility/strategy-ranker/).

Inheritance:
- [UtilityFunction](/ometeotl/documentation/class-reference/model/utility/utility-function/)

Constructor:
- `WeightedSumUtility(framework_id, metric_weights)`

Method:
- `evaluate(perception, actor, context) -> UtilityFrame`

Example:

```python
from ometeotl_core.game.utility import WeightedSumUtility

utility = WeightedSumUtility(
    framework_id="resource_efficiency",
    metric_weights={"energy": 0.6, "time": 0.4},
)

# Evaluate a perception for an actor (metrics come from context)
frame = utility.evaluate(
    perception,
    actor,
    context={"energy": 80.0, "time": 60.0},
)
print(frame.scalar_value)   # 0.6*80 + 0.4*60 = 72.0
print(frame.framework_id)   # "resource_efficiency"
```

See also:
- [LexicographicUtility](/ometeotl/documentation/class-reference/game/utility/lexicographic-utility/)
- [StrategyRanker](/ometeotl/documentation/class-reference/game/utility/strategy-ranker/)