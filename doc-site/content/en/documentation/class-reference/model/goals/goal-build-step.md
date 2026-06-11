---
title: "GoalBuildStep"
---

Source:
- [src/ometeotl_core/model/goals.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/goals.py)

Local role:
Recursive declarative node used to build goal hierarchies.

Big-picture role:
Input specification for hierarchy builders that construct [Goal](/ometeotl/documentation/class-reference/model/goals/goal/) trees without introducing domain-specific teleology.

Inheritance:
- dataclass

Fields:
- kind: str (`final` or `intermediate`)
- actor_id: str
- target_condition: dict
- horizon: dict
- priority: float
- status: str
- children: list[[GoalBuildStep](/ometeotl/documentation/class-reference/model/goals/goal-build-step/)]
- metadata: dict

Example:

```python
from ometeotl_core.model.goals import GoalBuildStep

# Describe a two-level goal hierarchy declaratively before materializing it
root_step = GoalBuildStep(
    kind="final",
    actor_id="actor-1",
    target_condition={"arrived": True},
    horizon={"window": 10},
    priority=1.0,
    status="active",
    children=[
        GoalBuildStep(
            kind="intermediate",
            actor_id="actor-1",
            target_condition={"en_route": True},
            priority=0.8,
            status="active",
        ),
    ],
)
```

See also:
- [Goal](/ometeotl/documentation/class-reference/model/goals/goal/)
- [GoalDecompositionTree](/ometeotl/documentation/class-reference/model/goals/goal-decomposition-tree/)