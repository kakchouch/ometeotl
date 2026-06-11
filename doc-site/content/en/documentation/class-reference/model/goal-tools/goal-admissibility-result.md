---
title: "GoalAdmissibilityResult"
---

Source:
- [src/ometeotl_core/model/goal_tools.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/goal_tools.py)

Local role:
Result container for actor-relative goal admissibility checks.

Fields:
- admissible: bool
- reason: str
- blocking_constraints: list[str]

Methods:
- `to_dict() -> dict`

Example:

```python
checker = GoalAdmissibilityChecker()
result = checker.check(goal, actor, perception)

print(result.admissible)            # True | False
print(result.reason)                # human-readable explanation
print(result.blocking_constraints)  # e.g. ["horizon_exceeded", "goal_not_linked"]

data = result.to_dict()
```

See also:
- [GoalAdmissibilityChecker](/ometeotl/documentation/class-reference/model/goal-tools/goal-admissibility-checker/)