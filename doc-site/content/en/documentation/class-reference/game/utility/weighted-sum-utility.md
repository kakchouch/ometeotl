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

See also:
- [LexicographicUtility](/ometeotl/documentation/class-reference/game/utility/lexicographic-utility/)
- [StrategyRanker](/ometeotl/documentation/class-reference/game/utility/strategy-ranker/)