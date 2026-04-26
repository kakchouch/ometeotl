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

See also:
- [WeightedSumUtility](/ometeotl/documentation/class-reference/game/utility/weighted-sum-utility/)
- [StrategyRanker](/ometeotl/documentation/class-reference/game/utility/strategy-ranker/)