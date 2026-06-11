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

Example:

```python
from ometeotl_core.model.strategies import StrategyBuildStep, build_branching_strategy

# Describe a branching strategy: action_a forks into two outcomes
root_step = StrategyBuildStep(
    action=action_a,
    branch_label="execute",
    children=[
        StrategyBuildStep(action=action_b, branch_label="on success", branch_probability=0.8),
        StrategyBuildStep(action=action_c, branch_label="on failure", branch_probability=0.2),
    ],
)
strategy = build_branching_strategy(
    id="strategy-1",
    actor_id="actor-1",
    step=root_step,
)
strategy.validate_tree()
```

See also:
- [StrategyNode](/ometeotl/documentation/class-reference/model/strategies/strategy-node/)
- [Strategy](/ometeotl/documentation/class-reference/model/strategies/strategy/)