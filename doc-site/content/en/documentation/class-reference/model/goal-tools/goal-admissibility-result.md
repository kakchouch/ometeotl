---
title: "GoalAdmissibilityResult"
---

Source:
- [src/masm/model/goal_tools.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/goal_tools.py)

Local role:
Result container for actor-relative goal admissibility checks.

Fields:
- admissible: bool
- reason: str
- blocking_constraints: list[str]

Methods:
- `to_dict() -> dict`

See also:
- [GoalAdmissibilityChecker](/ometeotl/documentation/class-reference/model/goal-tools/goal-admissibility-checker/)