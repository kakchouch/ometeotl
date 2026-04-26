---
title: "GoalAdmissibilityChecker"
---

Source:
- [src/ometeotl_core/model/goal_tools.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/goal_tools.py)

Local role:
Model-level F-13 checker for whether a goal is admissible for one actor under one perception.

Big-picture role:
Guardrail for actor-consistent objective evaluation before strategy ranking.

Inheritance:
- standard class

Method:
- `check(goal, actor, perception) -> GoalAdmissibilityResult`

Checks include:
- goal actor binding consistency
- goal linkage in actor relations
- blocking constraints from perception context
- optional horizon capacity constraints

See also:
- [Goal](/ometeotl/documentation/class-reference/model/goals/goal/)
- [Perception](/ometeotl/documentation/class-reference/model/perception/perception/)