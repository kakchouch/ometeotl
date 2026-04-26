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

See also:
- [RankedStrategy](/ometeotl/documentation/class-reference/game/utility/ranked-strategy/)
- [UtilityFunction](/ometeotl/documentation/class-reference/model/utility/utility-function/)