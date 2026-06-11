---
title: "GoalFeasibilityResult"
---

Source:
- [src/ometeotl_core/model/goal_tools.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/goal_tools.py)

Local role:
Result container for feasibility checks between a goal and a projected state.

Fields:
- reachable: bool
- confidence: float
- matching_keys: list[str]
- metadata: dict

Methods:
- `to_dict() -> dict`

Example:

```python
feas_tool = DefaultGoalFeasibilityTool()
result = feas_tool.evaluate(goal, projected_state)

print(result.reachable)       # True | False
print(result.confidence)      # float in [0, 1]
print(result.matching_keys)   # target_condition keys that matched

data = result.to_dict()
```

See also:
- [GoalFeasibilityTool](/ometeotl/documentation/class-reference/model/goal-tools/goal-feasibility-tool/)
- [DefaultGoalFeasibilityTool](/ometeotl/documentation/class-reference/model/goal-tools/default-goal-feasibility-tool/)