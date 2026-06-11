---
title: "RankedStrategy"
---

Source:
- [src/ometeotl_core/game/utility.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/game/utility.py)

Local role:
Result container for one evaluated strategy and its aggregate utility.

Fields:
- strategy: [Strategy](/ometeotl/documentation/class-reference/model/strategies/strategy/)
- utility_frame: [UtilityFrame](/ometeotl/documentation/class-reference/model/utility/utility-frame/)
- rank_key: tuple[float, ...]
- terminal_node_ids: list[str]
- terminal_probabilities: dict

Example:

```python
ranker = StrategyRanker(utility)
ranked_strategies = ranker.rank_strategies([strategy_a, strategy_b], actor)

best = ranked_strategies[0]           # highest utility
print(best.strategy.id)
print(best.utility_frame.scalar_value)
print(best.rank_key)                  # sorting tuple used for tie-breaking
print(best.terminal_node_ids)         # terminal nodes that contributed to the score
print(best.terminal_probabilities)    # {node_id: accumulated_probability}
```

See also:
- [StrategyRanker](/ometeotl/documentation/class-reference/game/utility/strategy-ranker/)