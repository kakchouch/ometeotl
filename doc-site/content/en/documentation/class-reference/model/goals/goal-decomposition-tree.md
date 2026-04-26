---
title: "GoalDecompositionTree"
---

Source:
- [src/ometeotl_core/model/goals.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/goals.py)

Local role:
Container for one goal hierarchy rooted at a single goal id.

Big-picture role:
Deterministic structure for intermediate-objective decomposition and hierarchy validation.

Inheritance:
- dataclass

Fields:
- root_goal_id: str
- goals: dict[str, [Goal](/ometeotl/documentation/class-reference/model/goals/goal/)]

Methods:
- `add_goal(goal) -> None`
- `get_goal(goal_id) -> Optional[Goal]`
- `children_of(goal_id) -> list[Goal]`
- `parent_of(goal_id) -> Optional[Goal]`
- `validate_tree() -> None`
- `to_dict() -> dict`
- `from_dict(data) -> GoalDecompositionTree`

See also:
- [Goal](/ometeotl/documentation/class-reference/model/goals/goal/)
- [GoalBuildStep](/ometeotl/documentation/class-reference/model/goals/goal-build-step/)