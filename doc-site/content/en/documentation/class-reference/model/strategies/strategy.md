---
title: "Strategy"
---

Source:
- [src/ometeotl_core/model/strategies.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/strategies.py)

Local role:
Declarative strategy tree composed of [StrategyNode](/ometeotl/documentation/class-reference/model/strategies/strategy-node/) objects and their [StrategyOutcomeBranch](/ometeotl/documentation/class-reference/model/strategies/strategy-outcome-branch/) links.

Big-picture role:
Current strategy-layer root object. It is the first model-level structure that chains action projections through successive perceived states.

Inheritance:
- [ModelObject](/ometeotl/documentation/class-reference/model/base/model-object/)

Parameters and fields:
- id: str
- actor_id: str
- goal_id: Optional[str]
- root_node_id: str
- nodes: list[[StrategyNode](/ometeotl/documentation/class-reference/model/strategies/strategy-node/)]
- projection_policy: str

Methods:
- `add_node(node) -> None`
- `get_node(node_id) -> Optional[StrategyNode]`
- `validate_tree() -> None`
- `to_dict() -> dict`
- `from_dict(data) -> Strategy`

Important behavior:
- validates that `root_node_id` exists
- validates branch ids are unique per node
- validates branch child references
- validates that child nodes consume the parent node's projected successor perception when a parent branch links to that child

Builder functions in the same source module:
- `build_linear_strategy(...)`
- `build_branching_strategy(...)`

See also:
- [StrategyBuildStep](/ometeotl/documentation/class-reference/model/strategies/strategy-build-step/)
- [StrategyNode](/ometeotl/documentation/class-reference/model/strategies/strategy-node/)