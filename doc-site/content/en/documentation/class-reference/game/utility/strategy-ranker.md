---
title: "StrategyRanker"
---

Source:
- [src/ometeotl_core/game/utility.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/game/utility.py)

Local role:
Ranks strategies by evaluating projected terminal nodes with a utility function.

Big-picture role:
Game-layer bridge from projected strategy structures to comparable utility outcomes.

Inheritance:
- standard class

Constructor:
- `StrategyRanker(utility_function)`

Methods:
- `evaluate_strategy(strategy, actor, context=None) -> RankedStrategy`
- `rank_strategies(strategies, actor, context=None) -> list[RankedStrategy]`

Important behavior:
- validates strategy trees before ranking
- aggregates branch probabilities per child node
- supports directed acyclic strategies with duplicate terminal paths by accumulating terminal path probabilities per node id
- supports scalar and multi-criteria utility outputs

Example:

```python
from ometeotl_core.game.utility import StrategyRanker, WeightedSumUtility

utility = WeightedSumUtility("fw", {"score": 1.0})
ranker = StrategyRanker(utility)

# Rank a candidate set of strategies for an actor
ranked = ranker.rank_strategies([strategy_a, strategy_b, strategy_c], actor)
for rs in ranked:
    print(rs.strategy.id, rs.utility_frame.scalar_value)

best = ranked[0]
print("Best strategy:", best.strategy.id)
```

See also:
- [RankedStrategy](/ometeotl/documentation/class-reference/game/utility/ranked-strategy/)
- [UtilityFunction](/ometeotl/documentation/class-reference/model/utility/utility-function/)