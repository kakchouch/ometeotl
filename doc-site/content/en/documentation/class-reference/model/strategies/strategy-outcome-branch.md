---
title: "StrategyOutcomeBranch"
---

Source:
- [src/ometeotl_core/model/strategies.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/strategies.py)

Local role:
One outcome branch leaving a [StrategyNode](/ometeotl/documentation/class-reference/model/strategies/strategy-node/) toward an optional child node. Carries the projected successor perceived state produced by the parent node's action.

Big-picture role:
Strategy tree edge that encodes the projected outcome of one action execution: its successor perceived state, probability, condition labels, and child-node reference. One action can now produce several distinct outcomes across sibling branches.

Inheritance:
- dataclass

Parameters and fields:
- branch_id: str
- label: str
- child_node_id: Optional[str]
- projected_state: Optional[[ProjectedPerceptionState](/ometeotl/documentation/class-reference/model/projection/projected-perception-state/)]
- probability: Optional[float]
- condition: dict
- metadata: dict

Methods:
- `to_dict() -> dict`
- `from_dict(data) -> StrategyOutcomeBranch`

Important behavior:
- if `projected_state` is present, `validate_tree()` on [Strategy](/ometeotl/documentation/class-reference/model/strategies/strategy/) enforces that its `generating_action_id` matches the parent node's `action_id`
- terminal branches (no `child_node_id`) may still carry a `projected_state` to expose the final successor perception to utility evaluation
- `probability` must be in `[0, 1]` when set

Example:

```python
from ometeotl_core.model.strategies import StrategyOutcomeBranch

# Terminal branch (no child): carries the projected final state
success_branch = StrategyOutcomeBranch(
    branch_id="branch-success",
    label="success",
    probability=0.8,
    condition={"resource_available": True},
    projected_state=projected_perception_state,
)

# Non-terminal branch: links to the next node
continue_branch = StrategyOutcomeBranch(
    branch_id="branch-continue",
    label="partial",
    child_node_id="node-2",
    probability=0.2,
)

data = success_branch.to_dict()
```

See also:
- [StrategyNode](/ometeotl/documentation/class-reference/model/strategies/strategy-node/)
- [Strategy](/ometeotl/documentation/class-reference/model/strategies/strategy/)
- [ProjectedPerceptionState](/ometeotl/documentation/class-reference/model/projection/projected-perception-state/)
