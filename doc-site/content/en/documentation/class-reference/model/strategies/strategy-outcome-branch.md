---
title: "StrategyOutcomeBranch"
---

Source:
- [src/masm/model/strategies.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/strategies.py)

Local role:
One branch edge leaving a [StrategyNode](/ometeotl/documentation/class-reference/model/strategies/strategy-node/) toward an optional child node.

Big-picture role:
Strategy tree edge model used to encode labels, probabilities, conditions, and child-node references.

Current note:
- The current implementation keeps projected successor state on the node, not on the branch.
- A future TODO prefers branch-specific projected outcomes here if one action later supports several distinct projected outcomes.

Inheritance:
- dataclass

Parameters and fields:
- branch_id: str
- label: str
- child_node_id: Optional[str]
- probability: Optional[float]
- condition: dict
- metadata: dict

Methods:
- `to_dict() -> dict`
- `from_dict(data) -> StrategyOutcomeBranch`

See also:
- [StrategyNode](/ometeotl/documentation/class-reference/model/strategies/strategy-node/)
- [Strategy](/ometeotl/documentation/class-reference/model/strategies/strategy/)