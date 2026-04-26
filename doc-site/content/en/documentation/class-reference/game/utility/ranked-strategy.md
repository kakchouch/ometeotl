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

See also:
- [StrategyRanker](/ometeotl/documentation/class-reference/game/utility/strategy-ranker/)