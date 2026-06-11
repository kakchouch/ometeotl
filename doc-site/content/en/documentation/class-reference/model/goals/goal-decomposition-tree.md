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

Example:

```python
from ometeotl_core.model.goals import Goal, GoalDecompositionTree

root = Goal(id="root", actor_id="actor-1", kind="final", priority=1.0,
            status="active", target_condition={"arrived": True})
sub = Goal(id="sub-1", actor_id="actor-1", kind="intermediate", priority=0.8,
           status="active", target_condition={"en_route": True},
           parent_goal_id="root")
root.add_child_goal("sub-1")

tree = GoalDecompositionTree(root_goal_id="root")
tree.add_goal(root)
tree.add_goal(sub)
tree.validate_tree()

children = tree.children_of("root")
parent = tree.parent_of("sub-1")   # returns root goal

data = tree.to_dict()
```

See also:
- [Goal](/ometeotl/documentation/class-reference/model/goals/goal/)
- [GoalBuildStep](/ometeotl/documentation/class-reference/model/goals/goal-build-step/)