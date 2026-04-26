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

See also:
- [GoalFeasibilityResult](/ometeotl/documentation/class-reference/model/goal-tools/goal-feasibility-result/)
- [GoalAdmissibilityChecker](/ometeotl/documentation/class-reference/model/goal-tools/goal-admissibility-checker/)