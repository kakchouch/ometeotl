---
title: "DefaultGoalFeasibilityTool"
---

Source:
- [src/ometeotl_core/model/goal_tools.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/goal_tools.py)

Local role:
Default implementation of [GoalFeasibilityTool](/ometeotl/documentation/class-reference/model/goal-tools/goal-feasibility-tool/) based on deterministic condition-key matching.

Big-picture role:
Baseline model-level feasibility evaluator used before domain-specific scoring or planners are introduced.

Inheritance:
- [GoalFeasibilityTool](/ometeotl/documentation/class-reference/model/goal-tools/goal-feasibility-tool/)

Method:
- `evaluate(goal, projected) -> GoalFeasibilityResult`

Example:

```python
from ometeotl_core.model.goal_tools import DefaultGoalFeasibilityTool
from ometeotl_core.model.projection import DefaultProjectionTool

proj_tool = DefaultProjectionTool()
proj = proj_tool.project_action(action, perception)

feas_tool = DefaultGoalFeasibilityTool()
result = feas_tool.evaluate(goal, proj.projected_state)

print(result.reachable)        # True | False
print(result.confidence)       # float in [0, 1]
print(result.matching_keys)    # target_condition keys that matched
```

See also:
- [GoalFeasibilityResult](/ometeotl/documentation/class-reference/model/goal-tools/goal-feasibility-result/)
- [GoalAdmissibilityChecker](/ometeotl/documentation/class-reference/model/goal-tools/goal-admissibility-checker/)