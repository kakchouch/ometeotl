---
title: "GoalFeasibilityResult"
---

Source:
- [src/masm/model/goal_tools.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/goal_tools.py)

Local role:
Result container for feasibility checks between a goal and a projected state.

Fields:
- reachable: bool
- confidence: float
- matching_keys: list[str]
- metadata: dict

Methods:
- `to_dict() -> dict`

See also:
- [GoalFeasibilityTool](/ometeotl/documentation/class-reference/model/goal-tools/goal-feasibility-tool/)
- [DefaultGoalFeasibilityTool](/ometeotl/documentation/class-reference/model/goal-tools/default-goal-feasibility-tool/)