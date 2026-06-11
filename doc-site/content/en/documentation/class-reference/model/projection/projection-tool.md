---
title: "ProjectionTool"
---

Source:
- [src/ometeotl_core/model/projection.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/projection.py)

Local role:
Abstract contract for deriving assumption sets and successor perceived states from [Action](/ometeotl/documentation/class-reference/model/actions/action/), [Perception](/ometeotl/documentation/class-reference/model/perception/perception/), and [Resource](/ometeotl/documentation/class-reference/model/resources/resource/) inputs.

Big-picture role:
Extensibility seam for projection logic that stays separate from strategy-node construction while still feeding it with projected successor states.

Inheritance:
- abstract base class

Methods:
- `project_action(action, perception, resources=()) -> ActionProjection`
- `project_actions(actions, perception, resources=()) -> ProjectionBatch`

Example:

```python
from ometeotl_core.model.projection import ProjectionTool, ActionProjection

class CustomProjectionTool(ProjectionTool):
    """Minimal projection tool: marks every action as 'projected' unconditionally."""

    def project_action(self, action, perception, resources=()):
        return ActionProjection(
            action_id=action.id,
            actor_id=action.actor_id,
            source_perception_id=perception.id,
            source_id=perception.source_id,
            status="projected",
            resource_ids=[r.id for r in resources],
            assumptions=[],
        )

# Batch projection is inherited from the base class
tool = CustomProjectionTool()
batch = tool.project_actions([action1, action2], perception)
```

See also:
- [DefaultProjectionTool](/ometeotl/documentation/class-reference/model/projection/default-projection-tool/)