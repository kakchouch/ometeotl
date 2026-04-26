---
title: "StrategyBuildStep"
---

Source:
- [src/ometeotl_core/model/strategies.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/strategies.py)

Local role:
Recursive builder specification used to describe a strategy tree before it is materialized into [StrategyNode](/ometeotl/documentation/class-reference/model/strategies/strategy-node/) objects.

Big-picture role:
Input format for minimal strategy construction APIs, especially `build_branching_strategy(...)`.

Inheritance:
- dataclass

Parameters and fields:
- action: [Action](/ometeotl/documentation/class-reference/model/actions/action/)
- children: list[[StrategyBuildStep](/ometeotl/documentation/class-reference/model/strategies/strategy-build-step/)]
- branch_label: str
- branch_probability: Optional[float]
- branch_condition: dict
- branch_metadata: dict
- metadata: dict

Methods:
- dataclass validation in `__post_init__()`

See also:
- [StrategyNode](/ometeotl/documentation/class-reference/model/strategies/strategy-node/)
- [Strategy](/ometeotl/documentation/class-reference/model/strategies/strategy/)