---
title: "Goal"
---

Source:
- [src/ometeotl_core/model/goals.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/goals.py)

Local role:
First-class objective model object for one actor.

Big-picture role:
Teleology representation primitive that remains domain-neutral while supporting final and intermediate objectives.

Inheritance:
- [ModelObject](/ometeotl/documentation/class-reference/model/base/model-object/)

Fields:
- id: str
- actor_id: str
- kind: str (`final` or `intermediate`)
- priority: float
- status: str
- horizon: dict
- target_condition: dict
- target_perception_id: Optional[str]
- parent_goal_id: Optional[str]
- child_goal_ids: list[str]
- strategy_ids: list[str]

Methods:
- `add_child_goal(goal_id) -> None`
- `remove_child_goal(goal_id) -> None`
- `add_strategy(strategy_id) -> None`
- `remove_strategy(strategy_id) -> None`
- `to_dict() -> dict`
- `from_dict(data) -> Goal`

Example:

```python
from ometeotl_core.model.goals import Goal

goal = Goal(
    id="goal-1",
    actor_id="actor-1",
    kind="final",
    priority=1.0,
    status="active",
    target_condition={"location": "target-zone"},
    horizon={"window": 10},
)
goal.add_strategy("strategy-1")

# Intermediate sub-goal
sub = Goal(
    id="goal-2",
    actor_id="actor-1",
    kind="intermediate",
    priority=0.8,
    status="active",
    target_condition={"step1": True},
    parent_goal_id="goal-1",
)
goal.add_child_goal("goal-2")

data = goal.to_dict()
goal2 = Goal.from_dict(data)
```

See also:
- [GoalDecompositionTree](/ometeotl/documentation/class-reference/model/goals/goal-decomposition-tree/)
- [Strategy](/ometeotl/documentation/class-reference/model/strategies/strategy/)