---
title: "StrategyNode"
---

Source:
- [src/ometeotl_core/model/strategies.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/strategies.py)

Local role:
Strategy node that binds one action id to one input perception and one projected successor perceived state.

Big-picture role:
Primary strategy-chain unit. A node says "apply this action from this perceived state, producing this projected successor perceived state."

Inheritance:
- dataclass

Parameters and fields:
- node_id: str
- action_id: str
- source_perception_id: Optional[str]
- projected_state: Optional[[ProjectedPerceptionState](/ometeotl/documentation/class-reference/model/projection/projected-perception-state/)]
- outcome_branches: list[[StrategyOutcomeBranch](/ometeotl/documentation/class-reference/model/strategies/strategy-outcome-branch/)]
- metadata: dict

Properties:
- `successor_perception_id -> Optional[str]`

Methods:
- `to_dict() -> dict`
- `from_dict(data) -> StrategyNode`

Important behavior:
- if `projected_state` is present, it must correspond to the node's `action_id`
- if `projected_state` is present, `source_perception_id` must match the projected state's source perception

See also:
- [StrategyOutcomeBranch](/ometeotl/documentation/class-reference/model/strategies/strategy-outcome-branch/)
- [Strategy](/ometeotl/documentation/class-reference/model/strategies/strategy/)