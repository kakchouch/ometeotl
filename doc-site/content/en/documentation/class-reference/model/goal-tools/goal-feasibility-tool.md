---
title: "GoalFeasibilityTool"
---

Source:
- [src/ometeotl_core/model/goal_tools.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/goal_tools.py)

Local role:
Abstract contract for evaluating whether a projected perception can satisfy a goal.

Big-picture role:
Model-level extensibility seam for feasibility logic, independent of any game domain scoring policy.

Inheritance:
- abstract base class

Method:
- `evaluate(goal, projected) -> GoalFeasibilityResult`

Example:

```python
from ometeotl_core.model.goal_tools import GoalFeasibilityTool, GoalFeasibilityResult

class SimpleFeasibilityTool(GoalFeasibilityTool):
    """Feasible when all target_condition keys match the projected state changes."""

    def evaluate(self, goal, projected):
        changes = {c.change_type for c in projected.changes}
        matched = [k for k in goal.target_condition if k in changes]
        reachable = len(matched) == len(goal.target_condition)
        return GoalFeasibilityResult(
            reachable=reachable,
            confidence=1.0 if reachable else 0.0,
            matching_keys=matched,
        )
```

See also:
- [Goal](/ometeotl/documentation/class-reference/model/goals/goal/)
- [ProjectedPerceptionState](/ometeotl/documentation/class-reference/model/projection/projected-perception-state/)