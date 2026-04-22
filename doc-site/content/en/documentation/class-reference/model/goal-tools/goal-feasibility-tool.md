---
title: "GoalFeasibilityTool"
---

Source:
- [src/masm/model/goal_tools.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/goal_tools.py)

Local role:
Abstract contract for evaluating whether a projected perception can satisfy a goal.

Big-picture role:
Model-level extensibility seam for feasibility logic, independent of any game domain scoring policy.

Inheritance:
- abstract base class

Method:
- `evaluate(goal, projected) -> GoalFeasibilityResult`

See also:
- [Goal](/ometeotl/documentation/class-reference/model/goals/goal/)
- [ProjectedPerceptionState](/ometeotl/documentation/class-reference/model/projection/projected-perception-state/)